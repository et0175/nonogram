// The /how-to-solve page (COMP-011, FR-045; CARD-419). See how-to-solve.html's
// header for what the page is and is not.
//
// Everything a board on this page shows is derived from the two grids below.
// No clue is typed anywhere: `cluesOf` computes them, so the page cannot
// print a number its own grid disagrees with. The grids, the probe cell and
// the probe chain are each one `export const` line of JSON-shaped literal so
// tests/test_how_to_solve_page.py can read the bytes the browser runs and
// check, with its own line solver and the brute-force oracle, that:
//   * TRY_GRID and PROBE_GRID each have exactly one solution;
//   * line logic alone leaves PROBE_GRID with exactly the open squares
//     PROBE_OPEN says, and PROBE_CELL is one of them;
//   * every step of PROBE_CHAIN is forced by its line once PROBE_CELL is
//     black, and the chain's last line can no longer fit its clue;
//   * with PROBE_CELL white, line logic finishes the grid.
//
// Static only (ADR-0041/R4): this file makes no request and touches no
// storage. A board resets on reload, which is what a lesson should do.

// "#" is black, "." is white. Rows top to bottom.
export const TRY_GRID = ["..#..", ".###.", "#####", "..#..", ".###."];
export const PROBE_GRID = ["#.#.#", ".....", "#...#", "#..##", ".###."];
// How many squares line logic leaves open on PROBE_GRID.
export const PROBE_OPEN = 8;
// The square the demo probes, [row, column], zero-based.
export const PROBE_CELL = [2, 1];
// What making PROBE_CELL black forces, in order: each step names the line
// that forces it and the squares it settles ([row, column, 1 black / 0 white]).
// The last step settles nothing: its line no longer fits its clue.
export const PROBE_CHAIN = [{"axis": "column", "index": 1, "cells": [[4, 1, 0]]}, {"axis": "row", "index": 2, "cells": [[2, 0, 0]]}, {"axis": "row", "index": 4, "cells": [[4, 0, 0], [4, 3, 1], [4, 4, 1]]}, {"axis": "column", "index": 0, "cells": []}];

// The guided steps of "Try one": which lines each step is about, by index.
export const TRY_STEPS = [{"rows": [2], "columns": []}, {"rows": [], "columns": [2]}, {"rows": [], "columns": [0, 4]}, {"rows": [0, 3], "columns": []}, {"rows": [1, 4], "columns": []}];

const STEP_NAMES = [
  "The rules",
  "Squeeze from both ends",
  "What every arrangement agrees on",
  "Probe, and watch it break",
  "The buttons",
  "Big puzzles on a phone",
  "Levels and the promise",
];

// --------------------------------------------------------------------------
// Clues
// --------------------------------------------------------------------------

// The runs of black squares in one line, as the page prints them: "0" for a
// line with none (the same rule the rest of the product uses, CLAUDE.md).
export function lineClue(cells) {
  const runs = [];
  let run = 0;
  for (const black of cells) {
    if (black) run += 1;
    else if (run > 0) {
      runs.push(run);
      run = 0;
    }
  }
  if (run > 0) runs.push(run);
  return runs.length === 0 ? [0] : runs;
}

export function cluesOf(grid) {
  const cells = grid.map((row) => [...row].map((ch) => ch === "#"));
  const height = cells.length;
  const width = cells[0].length;
  return {
    rows: cells.map(lineClue),
    columns: Array.from({ length: width }, (_, c) =>
      lineClue(Array.from({ length: height }, (_, r) => cells[r][c]))
    ),
  };
}

const solutionOf = (grid) => grid.map((row) => [...row].map((ch) => (ch === "#" ? "filled" : "empty")));
const words = (clue) => clue.join(" ");
const ordinal = (index) => String(index + 1);

// --------------------------------------------------------------------------
// One board: clues and buttons, redrawn from a state array
// --------------------------------------------------------------------------

const STATE_NAMES = { filled: "black", empty: "white", maybe: "maybe", unknown: "open" };

// A board element: a CSS grid of one clue column plus `width` cells, the
// column clues across the top. `cellState(r, c)` returns
// {state, probe, target, lit, bad}; `onTap(r, c)` handles a press.
function drawBoard(container, grid, view) {
  const { rows, columns } = cluesOf(grid);
  const height = rows.length;
  const width = columns.length;
  container.style.setProperty("--hts-columns", String(width));
  const parts = [];
  const corner = document.createElement("span");
  corner.className = "hts-clue hts-corner";
  parts.push(corner);
  columns.forEach((clue, c) => {
    const cell = document.createElement("span");
    cell.className = "hts-clue hts-clue-column";
    cell.textContent = clue.join("\n");
    cell.dataset.column = String(c);
    if (view.litColumn(c)) cell.classList.add("is-lit");
    if (view.badColumn(c)) cell.classList.add("is-bad");
    parts.push(cell);
  });
  for (let r = 0; r < height; r += 1) {
    const clue = document.createElement("span");
    clue.className = "hts-clue hts-clue-row";
    clue.textContent = words(rows[r]);
    clue.dataset.row = String(r);
    if (view.litRow(r)) clue.classList.add("is-lit");
    if (view.badRow(r)) clue.classList.add("is-bad");
    parts.push(clue);
    for (let c = 0; c < width; c += 1) {
      const info = view.cell(r, c);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hts-cell";
      button.dataset.row = String(r);
      button.dataset.column = String(c);
      button.dataset.state = info.state;
      if (info.probe) button.dataset.probe = "true";
      if (info.target) button.dataset.target = "true";
      if (view.litRow(r) || view.litColumn(c)) button.classList.add("is-lit");
      if (view.badColumn(c) || view.badRow(r)) button.classList.add("is-bad");
      button.setAttribute(
        "aria-label",
        `Row ${r + 1}, column ${c + 1}, ${STATE_NAMES[info.state]}${info.probe ? ", in the probe" : ""}`
      );
      button.addEventListener("click", () => view.tap(r, c));
      parts.push(button);
    }
  }
  container.replaceChildren(...parts);
}

// --------------------------------------------------------------------------
// "Try one": a guided 5x5 with the player's three marks
// --------------------------------------------------------------------------

function tryText(step, clues) {
  const r = (i) => words(clues.rows[i]);
  const c = (i) => words(clues.columns[i]);
  switch (step) {
    case 0:
      return `Tap a square to make it black. Row 3 says ${r(2)}, and the row is 5 squares wide, so every square in it is black.`;
    case 1:
      return `Column 3 says ${c(2)} too. Make the whole column black.`;
    case 2:
      return `Columns 1 and 5 say ${c(0)}, and that one square is already black. Choose White and mark the rest of those two columns white.`;
    case 3:
      return `Rows 1 and 4 say ${r(0)}, and their square is black already. Mark the other squares in those rows white.`;
    default:
      return `Rows 2 and 5 say ${r(1)}. Both ends are white now, so the ${r(1)} fits only in the middle. Make it black.`;
  }
}

// What a tap does, the player's rule (solver_state.js clickedState),
// reimplemented here because the lesson ships no player code: a tap paints
// the brush; tapping the same square again, or a square already holding the
// brush, steps it on — black, white, clear, black for the colour brushes,
// maybe and clear for Maybe. tests/test_how_to_solve_page.py runs both over
// every state, brush and repeat and holds them equal (CARD-444).
const COLOUR_ORDER = { filled: "empty", empty: "unknown", unknown: "filled" };
const MAYBE_ORDER = { maybe: "unknown", unknown: "maybe" };
export function tappedState(state, brush, repeat) {
  const order = brush === "maybe" ? MAYBE_ORDER : COLOUR_ORDER;
  if (!Object.hasOwn(order, state)) return brush;
  if (repeat === true || state === brush) return order[state];
  return brush;
}

function setupTry(page) {
  const board = page.querySelector("[data-hts-try-board]");
  if (board === null) return null;
  const text = page.querySelector("[data-hts-try-text]");
  const tag = page.querySelector("[data-hts-try-tag]");
  const brushes = [...page.querySelectorAll("[data-hts-brush]")];
  const solution = solutionOf(TRY_GRID);
  const clues = cluesOf(TRY_GRID);
  const height = TRY_GRID.length;
  const width = TRY_GRID[0].length;
  let cells;
  let brush = "filled";
  let lastTap = null; // [r, c, brush] of the last tap, for the repeat rule

  const inStep = (step, r, c) => TRY_STEPS[step].rows.includes(r) || TRY_STEPS[step].columns.includes(c);
  const stepDone = (step) => {
    for (let r = 0; r < height; r += 1)
      for (let c = 0; c < width; c += 1)
        if (inStep(step, r, c) && cells[r][c] !== solution[r][c]) return false;
    return true;
  };
  // Solved when the black squares are exactly the picture's: whites need
  // not be marked, which is how the player decides it too (by the clues).
  const solved = () =>
    cells.every((row, r) => row.every((state, c) => (state === "filled") === (solution[r][c] === "filled")));
  const currentStep = () => {
    let step = 0;
    while (step < TRY_STEPS.length - 1 && stepDone(step)) step += 1;
    return step;
  };

  function redraw() {
    const done = solved();
    const step = currentStep();
    drawBoard(board, TRY_GRID, {
      cell: (r, c) => ({ state: cells[r][c] }),
      litRow: (r) => !done && TRY_STEPS[step].rows.includes(r),
      litColumn: (c) => !done && TRY_STEPS[step].columns.includes(c),
      badRow: () => false,
      badColumn: () => false,
      tap: (r, c) => {
        const repeat = lastTap !== null && lastTap[0] === r && lastTap[1] === c && lastTap[2] === brush;
        cells[r][c] = tappedState(cells[r][c], brush, repeat);
        lastTap = [r, c, brush];
        redraw();
      },
    });
    board.dataset.solved = done ? "true" : "false";
    board.dataset.step = String(step + 1);
    tag.textContent = done ? "Solved" : `Step ${step + 1} of ${TRY_STEPS.length}`;
    text.textContent = done
      ? "You solved it: a little tree. Every puzzle works the same way, just bigger."
      : tryText(step, clues);
  }

  function choose(name) {
    brush = name;
    lastTap = null;
    for (const button of brushes) button.setAttribute("aria-pressed", String(button.dataset.htsBrush === name));
  }
  for (const button of brushes) button.addEventListener("click", () => choose(button.dataset.htsBrush));

  page.querySelector("[data-hts-try-show]")?.addEventListener("click", () => {
    if (solved()) return;
    const step = currentStep();
    for (let r = 0; r < height; r += 1)
      for (let c = 0; c < width; c += 1) if (inStep(step, r, c)) cells[r][c] = solution[r][c];
    // The next step after the two black lines is about whites: hand the
    // reader the brush it needs rather than leaving Black selected.
    const next = currentStep();
    choose(next === 2 || next === 3 ? "empty" : "filled");
    redraw();
  });
  const reset = () => {
    cells = Array.from({ length: height }, () => Array(width).fill("unknown"));
    lastTap = null;
    choose("filled");
    redraw();
  };
  page.querySelector("[data-hts-try-reset]")?.addEventListener("click", reset);
  reset();
  return { getCells: () => cells.map((row) => [...row]), isSolved: solved };
}

// --------------------------------------------------------------------------
// The squeeze picture
// --------------------------------------------------------------------------

function setupSqueeze(page) {
  const box = page.querySelector("[data-hts-squeeze]");
  if (box === null) return;
  const length = 10;
  const run = 8;
  const rows = [
    { label: "Pushed left", from: 0, to: run - 1, state: "maybe" },
    { label: "Pushed right", from: length - run, to: length - 1, state: "maybe" },
    { label: "Sure: black", from: length - run, to: run - 1, state: "filled" },
  ];
  box.replaceChildren(
    ...rows.map((row) => {
      const line = document.createElement("div");
      line.className = "hts-strip";
      const label = document.createElement("span");
      label.className = "hts-strip-label";
      label.textContent = row.label;
      const cells = document.createElement("div");
      cells.className = "hts-strip-cells";
      cells.setAttribute("role", "img");
      cells.setAttribute(
        "aria-label",
        `${row.label}: squares ${row.from + 1} to ${row.to + 1} ${row.state === "filled" ? "black" : "maybe"}`
      );
      for (let k = 0; k < length; k += 1) {
        const cell = document.createElement("span");
        cell.className = "hts-strip-cell";
        cell.dataset.state = k >= row.from && k <= row.to ? row.state : "unknown";
        cells.append(cell);
      }
      line.append(label, cells);
      return line;
    })
  );
}

// --------------------------------------------------------------------------
// "Try a probe": the player's Probe / Keep / Wrong guess, and the "Mark it?"
// offer a wrong guess on one square makes (CARD-412), on a real stall
// --------------------------------------------------------------------------

// Line logic alone: repeat "keep what every arrangement agrees on" over every
// row and column until nothing changes. Returns the settled board (cells
// "filled" / "empty" / "unknown"), or null if some line cannot fit at all.
// This is what fills the stalled starting board and "Finish with line logic";
// the test tree checks it against an independent solver.
function arrangements(clue, length) {
  const runs = clue[0] === 0 ? [] : clue;
  const out = [];
  const place = (index, start, line) => {
    if (index === runs.length) {
      out.push(line.concat(Array(length - line.length).fill(false)));
      return;
    }
    const rest = runs.slice(index + 1).reduce((sum, run) => sum + run + 1, 0);
    for (let at = start; at + runs[index] + rest <= length; at += 1) {
      const next = line.concat(Array(at - line.length).fill(false), Array(runs[index]).fill(true));
      if (index + 1 < runs.length) next.push(false);
      place(index + 1, next.length, next);
    }
  };
  place(0, 0, []);
  return out;
}

export function lineSolve(grid, start) {
  const { rows, columns } = cluesOf(grid);
  const height = rows.length;
  const width = columns.length;
  const cells = start.map((row) => [...row]);
  const lines = [
    ...rows.map((clue, r) => ({ clue, at: (k) => [r, k], length: width })),
    ...columns.map((clue, c) => ({ clue, at: (k) => [k, c], length: height })),
  ];
  let changed = true;
  while (changed) {
    changed = false;
    for (const line of lines) {
      const known = Array.from({ length: line.length }, (_, k) => {
        const [r, c] = line.at(k);
        return cells[r][c];
      });
      const fits = arrangements(line.clue, line.length).filter((option) =>
        option.every((black, k) => known[k] === "unknown" || known[k] === "maybe" || (known[k] === "filled") === black)
      );
      if (fits.length === 0) return null;
      for (let k = 0; k < line.length; k += 1) {
        if (known[k] === "filled" || known[k] === "empty") continue;
        if (fits.every((option) => option[k] === fits[0][k])) {
          const [r, c] = line.at(k);
          cells[r][c] = fits[0][k] ? "filled" : "empty";
          changed = true;
        }
      }
    }
  }
  return cells;
}

function probeText(phase, step, clues) {
  const line = (entry) =>
    entry.axis === "row"
      ? `Row ${ordinal(entry.index)} says ${words(clues.rows[entry.index])}`
      : `Column ${ordinal(entry.index)} says ${words(clues.columns[entry.index])}`;
  const [pr, pc] = PROBE_CELL;
  const where = `row ${ordinal(pr)}, column ${ordinal(pc)}`;
  switch (phase) {
    case "stuck":
      return `Lines are stuck here: no row or column can settle any of the ${PROBE_OPEN} open squares. Press Probe, then make the outlined square (${where}) black.`;
    case "open":
      return "Probe is on. Tap the outlined square to make it black. It gets a dashed edge, like everything you mark until you close the probe.";
    case "following":
      if (step === 0) return "Now follow what that black square forces. Press Follow it.";
      return `${line(PROBE_CHAIN[step - 1])}, so ${describe(PROBE_CHAIN[step - 1].cells)}.`;
    case "broken":
      return `${line(PROBE_CHAIN.at(-1))}, and it can no longer fit. The probe broke. Keep, or Wrong guess?`;
    case "kept":
      return "Keep would leave a line that cannot fit its clue, so this probe cannot be right. Press Wrong guess.";
    case "offered":
      return "Every dashed mark is gone. Your first square was the guess that broke, so the page offers to mark it the other colour.";
    case "proved":
      return `${where[0].toUpperCase()}${where.slice(1)} is now white: the probe proved it. Now the lines can move again.`;
    default:
      return "Solved. That is all a probe is: try one square, follow it, then keep it or take it all back.";
  }
}

function describe(cells) {
  const name = ([r, c, black]) => `row ${ordinal(r)}, column ${ordinal(c)} is ${black ? "black" : "white"}`;
  return cells.map(name).join(", ");
}

function setupProbe(page) {
  const board = page.querySelector("[data-hts-probe-board]");
  if (board === null) return null;
  const text = page.querySelector("[data-hts-probe-text]");
  const tag = page.querySelector("[data-hts-probe-tag]");
  const buttons = {
    open: page.querySelector("[data-hts-probe-open]"),
    follow: page.querySelector("[data-hts-probe-follow]"),
    keep: page.querySelector("[data-hts-probe-keep]"),
    abandon: page.querySelector("[data-hts-probe-abandon]"),
    mark: page.querySelector("[data-hts-probe-mark]"),
    dismiss: page.querySelector("[data-hts-probe-dismiss]"),
    finish: page.querySelector("[data-hts-probe-finish]"),
    reset: page.querySelector("[data-hts-probe-reset]"),
  };
  const clues = cluesOf(PROBE_GRID);
  const height = PROBE_GRID.length;
  const width = PROBE_GRID[0].length;
  const blank = Array.from({ length: height }, () => Array(width).fill("unknown"));
  const stalled = lineSolve(PROBE_GRID, blank);
  const [pr, pc] = PROBE_CELL;
  const where = `row ${ordinal(pr)}, column ${ordinal(pc)}`;
  let phase = "stuck";
  let step = 0;

  function board_() {
    const cells = stalled.map((row) => row.map((state) => ({ state, probe: false })));
    if (phase === "following" || phase === "broken" || phase === "kept") {
      cells[pr][pc] = { state: "filled", probe: true };
      for (let k = 0; k < step; k += 1)
        for (const [r, c, black] of PROBE_CHAIN[k].cells) cells[r][c] = { state: black ? "filled" : "empty", probe: true };
    }
    if (phase === "proved") cells[pr][pc] = { state: "empty", probe: false };
    if (phase === "solved") {
      const start = stalled.map((row) => [...row]);
      start[pr][pc] = "empty";
      const done = lineSolve(PROBE_GRID, start);
      return done.map((row) => row.map((state) => ({ state, probe: false })));
    }
    return cells;
  }

  function redraw() {
    const cells = board_();
    const showing = phase === "following" && step > 0 ? PROBE_CHAIN[step - 1] : phase === "broken" || phase === "kept" ? PROBE_CHAIN.at(-1) : null;
    const bad = phase === "broken" || phase === "kept";
    const offer = page.querySelector("[data-hts-probe-offer]");
    const lit = (axis, index) => showing !== null && showing.axis === axis && showing.index === index;
    drawBoard(board, PROBE_GRID, {
      cell: (r, c) => ({ ...cells[r][c], target: (phase === "stuck" || phase === "open") && r === pr && c === pc }),
      litRow: (r) => lit("row", r) && !bad,
      litColumn: (c) => lit("column", c) && !bad,
      badRow: (r) => bad && lit("row", r),
      badColumn: (c) => bad && lit("column", c),
      tap: (r, c) => {
        if (phase === "open" && r === pr && c === pc) {
          phase = "following";
          step = 0;
          redraw();
        }
      },
    });
    board.dataset.phase = phase;
    const open = phase === "open" || phase === "following" || phase === "broken" || phase === "kept";
    buttons.open.hidden = !(phase === "stuck" || phase === "open");
    buttons.open.setAttribute("aria-pressed", String(open));
    buttons.follow.hidden = phase !== "following";
    buttons.keep.hidden = !(phase === "broken" || phase === "kept");
    buttons.abandon.hidden = !(phase === "broken" || phase === "kept");
    // The player flags Wrong guess while the probe has broken a line (CARD-410).
    buttons.abandon.classList.toggle("is-flagged", bad);
    offer.hidden = phase !== "offered";
    page.querySelector("[data-hts-probe-offer-text]").textContent =
      `Your first guess was wrong, so ${where} must be white. Mark it?`;
    buttons.finish.hidden = phase !== "proved";
    buttons.reset.hidden = phase !== "solved";
    tag.textContent = phase === "solved" ? "Solved" : open ? "Probe open" : "Line logic stuck";
    // The square the offer names is outlined, as the player outlines it.
    board.querySelector(`.hts-cell[data-row="${pr}"][data-column="${pc}"]`)
      ?.classList.toggle("is-offered", phase === "offered");
    text.textContent = probeText(phase, step, clues);
  }

  buttons.open.addEventListener("click", () => {
    if (phase === "stuck") {
      phase = "open";
      redraw();
    }
  });
  buttons.follow.addEventListener("click", () => {
    step += 1;
    if (step >= PROBE_CHAIN.length) phase = "broken";
    redraw();
  });
  buttons.keep.addEventListener("click", () => {
    phase = "kept";
    redraw();
  });
  buttons.abandon.addEventListener("click", () => {
    phase = "offered";
    step = 0;
    redraw();
  });
  buttons.mark.addEventListener("click", () => {
    phase = "proved";
    redraw();
  });
  buttons.dismiss.addEventListener("click", () => {
    phase = "stuck";
    redraw();
  });
  buttons.finish.addEventListener("click", () => {
    phase = "solved";
    redraw();
  });
  buttons.reset.addEventListener("click", () => {
    phase = "stuck";
    step = 0;
    redraw();
  });
  redraw();
  return { getPhase: () => phase };
}

// --------------------------------------------------------------------------
// The wizard
// --------------------------------------------------------------------------

// Where "Back to your puzzles" goes: the book landing the reader came from
// when the referrer is a /b/<slug> on this site, else the library. Read from
// document.referrer, never stored.
export function homeHref(referrer, origin) {
  try {
    const from = new URL(referrer);
    if (from.origin === origin && /^\/b\/[0-9a-f]{10}$/.test(from.pathname)) return from.pathname;
  } catch {
    // No referrer, or not a URL: the library.
  }
  return "/library";
}

function stepFromHash(hash) {
  const n = Number.parseInt(String(hash).replace(/^#/, ""), 10);
  return Number.isInteger(n) && n >= 1 && n <= STEP_NAMES.length ? n : 1;
}

function setupWizard(page) {
  const steps = [...page.querySelectorAll("[data-hts-step]")];
  const dots = [...page.querySelectorAll("[data-hts-goto]")];
  const caption = page.querySelector("[data-hts-caption]");
  const back = page.querySelector("[data-hts-back]");
  const next = page.querySelector("[data-hts-next]");
  let current = 1;

  function show(n, focus) {
    current = n;
    for (const step of steps) step.hidden = Number(step.dataset.htsStep) !== n;
    dots.forEach((dot) => {
      const k = Number(dot.dataset.htsGoto);
      dot.dataset.done = String(k <= n);
      if (k === n) dot.setAttribute("aria-current", "step");
      else dot.removeAttribute("aria-current");
    });
    caption.textContent = `Step ${n} of ${STEP_NAMES.length} · ${STEP_NAMES[n - 1]}`;
    back.hidden = n === 1;
    next.hidden = n === STEP_NAMES.length;
    next.textContent = n < STEP_NAMES.length ? `Next: ${STEP_NAMES[n]}` : "";
    if (focus) page.querySelector(`[data-hts-step="${n}"] h2`)?.focus?.();
  }
  const go = (n) => {
    if (window.location.hash !== `#${n}`) window.location.hash = String(n);
    else show(n, true);
  };
  for (const dot of dots) dot.addEventListener("click", () => go(Number(dot.dataset.htsGoto)));
  back.addEventListener("click", () => go(Math.max(1, current - 1)));
  next.addEventListener("click", () => go(Math.min(STEP_NAMES.length, current + 1)));
  window.addEventListener("hashchange", () => show(stepFromHash(window.location.hash), true));
  for (const heading of page.querySelectorAll("[data-hts-step] h2")) heading.tabIndex = -1;
  show(stepFromHash(window.location.hash), false);
  return { getStep: () => current };
}

function load() {
  const page = document.querySelector("[data-hts-page]");
  if (page === null) return;
  const home = homeHref(document.referrer, window.location.origin);
  for (const link of page.querySelectorAll("[data-hts-home]")) link.setAttribute("href", home);
  const wizard = setupWizard(page);
  const tryBoard = setupTry(page);
  setupSqueeze(page);
  const probe = setupProbe(page);
  window.howToSolve = {
    getStep: wizard.getStep,
    getTryCells: tryBoard.getCells,
    isTrySolved: tryBoard.isSolved,
    getProbePhase: probe.getPhase,
    home,
  };
}

if (typeof document !== "undefined") load();
