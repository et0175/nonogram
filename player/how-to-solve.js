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
// CARD-445: the player's own rules, imported rather than copied: what a tap
// does (clickedState) and which clue numbers are circled (circledNumbers).
// solver_state.js is served at the site root as the play page's byte-
// identical copy (ADR-0041/R3), so the lesson runs exactly the player's code.
import { circledNumbers, clickedState } from "/solver_state.js";

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
  const states = Array.from({ length: height }, (_, r) =>
    Array.from({ length: width }, (_, c) => view.cell(r, c).state));
  // A clue box: one span per number, circled exactly where the player would
  // circle it on these marks (CARD-445).
  const numbers = (box, clue, cells) => {
    const circled = circledNumbers(clue, cells);
    box.replaceChildren(...clue.map((value, k) => {
      const number = document.createElement("span");
      number.className = "hts-num";
      number.classList.toggle("is-circled", circled[k]);
      number.textContent = String(value);
      return number;
    }));
    box.setAttribute("aria-label", `Clue ${words(clue)}`);
  };
  const parts = [];
  const corner = document.createElement("span");
  corner.className = "hts-clue hts-corner";
  parts.push(corner);
  columns.forEach((clue, c) => {
    const cell = document.createElement("span");
    cell.className = "hts-clue hts-clue-column";
    numbers(cell, clue, states.map((row) => row[c]));
    cell.dataset.column = String(c);
    if (view.litColumn(c)) cell.classList.add("is-lit");
    if (view.badColumn(c)) cell.classList.add("is-bad");
    parts.push(cell);
  });
  for (let r = 0; r < height; r += 1) {
    const clue = document.createElement("span");
    clue.className = "hts-clue hts-clue-row";
    numbers(clue, rows[r], states[r]);
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
      // The player's ruled grid (CARD-445): a heavy rule after every fifth
      // line and around the frame, a thin one between the rest.
      if (c === 0) button.classList.add("is-left");
      if (r === 0) button.classList.add("is-top");
      if ((c + 1) % 5 === 0 || c === width - 1) button.classList.add("major-right");
      if ((r + 1) % 5 === 0 || r === height - 1) button.classList.add("major-below");
      if (info.probe) button.dataset.probe = "true";
      if (info.target) button.dataset.target = "true";
      if (view.litRow(r) || view.litColumn(c)) button.classList.add("is-lit");
      button.setAttribute(
        "aria-label",
        `Row ${r + 1}, column ${c + 1}, ${STATE_NAMES[info.state]}${info.probe ? ", in the probe" : ""}`
      );
      button.addEventListener("click", () => view.tap(r, c));
      parts.push(button);
    }
  }
  // Review of 2026-11-17: every press redraws the board, and replacing the
  // focused square dropped a keyboard reader back to the top of the page.
  // The square that takes its place takes the focus too.
  const held = container.contains(document.activeElement) ? document.activeElement.dataset : null;
  container.replaceChildren(...parts);
  if (held?.row !== undefined && held.column !== undefined) {
    container.querySelector(`.hts-cell[data-row="${held.row}"][data-column="${held.column}"]`)?.focus();
  }
  wireCrosshair(container);
}

// The player's crosshair (CARD-267): the row and the column of the square
// under the pointer, and their clue boxes, tinted. Wired once per board and
// re-applied after a redraw from the square it last pointed at.
function wireCrosshair(container) {
  const paint = (at) => {
    for (const element of container.querySelectorAll(".is-crossed")) element.classList.remove("is-crossed");
    if (at === null) return;
    const [r, c] = at;
    for (const element of container.querySelectorAll(
      `.hts-cell[data-row="${r}"], .hts-cell[data-column="${c}"], .hts-clue-row[data-row="${r}"], .hts-clue-column[data-column="${c}"]`
    )) element.classList.add("is-crossed");
  };
  if (container.dataset.crosshair !== "wired") {
    container.dataset.crosshair = "wired";
    container.addEventListener("pointerover", (event) => {
      const cell = event.target instanceof Element ? event.target.closest(".hts-cell") : null;
      if (cell === null) return;
      container.htsCrossed = [cell.dataset.row, cell.dataset.column];
      paint(container.htsCrossed);
    });
    container.addEventListener("pointerleave", () => {
      container.htsCrossed = null;
      paint(null);
    });
  }
  paint(container.htsCrossed ?? null);
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
      return `Column 3 says ${c(2)} too, and its middle square is black already. Make the other four black.`;
    case 2:
      return `Columns 1 and 5 say ${c(0)}, and that one square is already black. Choose White and mark the rest of those two columns white.`;
    case 3:
      return `Rows 1 and 4 say ${r(0)}, and their square is black already. Mark the other squares in those rows white.`;
    default:
      return `Rows 2 and 5 say ${r(1)}. Both ends are white now, so the ${r(1)} fits only in the middle. Make it black.`;
  }
}

// What a tap does is the player's own rule, imported (clickedState): a tap
// paints the brush; tapping the same square again, or a square already
// holding the brush, steps it on — black, white, clear for the colour
// brushes, maybe and clear for Maybe (CARD-444 copied it; CARD-445 imports it).
export const tappedState = clickedState;

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
    // CARD-470 (UX review L3): not a second "Step ... of ..." a few lines
    // under the wizard's own; this one counts the exercise's moves.
    tag.textContent = done ? "Solved" : `Try it: ${step + 1}/${TRY_STEPS.length}`;
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
// The agreement picture (review of 2026-11-17, pass 2, item 13: step 3 was
// text only while steps 2 and 4 had figures). A row of 10 with the clue 3 and
// its second square already black: the two arrangements that still fit, and
// what both agree on, the whites included, which the squeeze alone would not
// give. The arrangements are the lesson's own (arrangements, below), so the
// figure cannot disagree with the clue it shows.
// --------------------------------------------------------------------------

function setupAgree(page) {
  const box = page.querySelector("[data-hts-agree]");
  if (box === null) return;
  const length = 10;
  const known = 1;
  const ways = arrangements([3], length).filter((line) => line[known]);
  const agreed = Array.from({ length }, (_, k) => (ways.every((line) => line[k]) ? "filled"
    : ways.every((line) => !line[k]) ? "empty" : "unknown"));
  const rows = [
    { label: "You know", cells: Array.from({ length }, (_, k) => (k === known ? "filled" : "unknown")) },
    ...ways.map((line, i) => ({ label: i === 0 ? "One way" : "The other", cells: line.map((on) => (on ? "maybe" : "unknown")) })),
    { label: "Both agree", cells: agreed },
  ];
  const said = { filled: "black", empty: "white", maybe: "covered", unknown: "open" };
  box.replaceChildren(...rows.map((row) => {
    const line = document.createElement("div");
    line.className = "hts-strip";
    const label = document.createElement("span");
    label.className = "hts-strip-label";
    label.textContent = row.label;
    const cells = document.createElement("div");
    cells.className = "hts-strip-cells";
    cells.setAttribute("role", "img");
    cells.setAttribute("aria-label", `${row.label}: ${row.cells.map((state, k) => `${k + 1} ${said[state]}`).join(", ")}`);
    for (const state of row.cells) {
      const cell = document.createElement("span");
      cell.className = "hts-strip-cell";
      cell.dataset.state = state;
      cells.append(cell);
    }
    line.append(label, cells);
    return line;
  }));
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
    hint: page.querySelector("[data-hts-probe-hint]"),
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
  // CARD-435's quiet probe: a broken line is shown only once Hint is pressed
  // during the probe, and any further step hides it again (the player resets
  // it on every recorded change). `said` is that press's sentence.
  let asked = false;
  let said = null;
  let pressed = null; // the button whose press this redraw answers

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
    const bad = (phase === "broken" || phase === "kept") && asked;
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
    buttons.hint.hidden = !(phase === "following" || phase === "broken" || phase === "kept");
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
    text.textContent = said ?? probeText(phase, step, clues);
    // A button that was pressed and then hid itself (Follow it at the last
    // step, Wrong guess, Mark it, Finish) hands the focus to the first one
    // still offered, for the same reason drawBoard keeps a square's.
    if (pressed !== null && (pressed.hidden || pressed.closest("[hidden]") !== null)) {
      (Object.values(buttons).find((button) => !button.hidden && !button.closest("[hidden]")) ?? board).focus?.();
    }
    pressed = null;
  }

  // Every press but Hint is a new input: the answer Hint gave is withdrawn.
  for (const button of Object.values(buttons)) {
    if (button !== buttons.hint) button.addEventListener("click", () => { asked = false; said = null; }, { capture: true });
    // Forgotten again once this press has been answered: a press that draws
    // nothing (Probe pressed twice) must not leave a button remembered for
    // the NEXT redraw to hand the focus to.
    button.addEventListener("click", () => {
      pressed = button;
      // A task, not a microtask: microtasks run BETWEEN the listeners of a
      // real press, which would forget the button before its own handler
      // has redrawn.
      setTimeout(() => { pressed = null; }, 0);
    }, { capture: true });
  }
  board.addEventListener("click", () => { asked = false; said = null; }, { capture: true });
  buttons.hint.addEventListener("click", () => {
    asked = true;
    // The player's own sentences (solver.js probeBrokenText).
    const broken = phase === "broken" || phase === "kept" ? [PROBE_CHAIN.at(-1)] : [];
    said = broken.length === 0
      ? "Hint: this guess breaks no row or column yet."
      : `Hint: this guess breaks ${broken.map((entry) => `${entry.axis} ${entry.index + 1}`).join(", ")}.`;
    redraw();
  });
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
// when the referrer is a /b/<slug> on this site — or one of that book's
// puzzles, /play/<key>?book=<slug>, which is where the lesson's link on the
// play page is pressed (review of 2026-11-17: that reader was sent to the
// library and lost the book's look) — else the library. Read from
// document.referrer, never stored.
export function homeHref(referrer, origin) {
  try {
    const from = new URL(referrer);
    if (from.origin === origin && /^\/b\/[0-9a-f]{10}$/.test(from.pathname)) return from.pathname;
    const book = from.searchParams.get("book") ?? "";
    if (from.origin === origin && /^\/play\/[0-9a-f]{10}$/.test(from.pathname)
        && /^[0-9a-f]{10}$/.test(book)) return `/b/${book}`;
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
  const narrow = window.matchMedia("(max-width: 600px)");
  function nextLabel() {
    const n = current;
    if (n >= STEP_NAMES.length) {
      next.textContent = "";
      next.removeAttribute("aria-label");
      return;
    }
    next.textContent = narrow.matches ? "Next" : `Next: ${STEP_NAMES[n]}`;
    next.setAttribute("aria-label", `Next: ${STEP_NAMES[n]}`);
  }
  narrow.addEventListener("change", nextLabel);

  function show(n, focus) {
    current = n;
    for (const step of steps) step.hidden = Number(step.dataset.htsStep) !== n;
    dots.forEach((dot) => {
      const k = Number(dot.dataset.htsGoto);
      dot.dataset.done = String(k <= n);
      if (k === n) dot.setAttribute("aria-current", "step");
      else dot.removeAttribute("aria-current");
    });
    // Review of 2026-11-17, pass 2 (item 15): the step's name is its heading,
    // so the caption says only where in the lesson the reader is.
    caption.textContent = `Step ${n} of ${STEP_NAMES.length}`;
    back.hidden = n === 1;
    next.hidden = n === STEP_NAMES.length;
    // Item 16: the next step's name is dropped on a narrow screen, where a
    // long one wrapped the button and stacked Back above it; the accessible
    // name keeps it.
    nextLabel();
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

// CARD-463 (UX review M7): opened from a book's landing, the lesson wears
// that book's theme, read from the book's own file exactly as the landing
// and the play page read it; anything else keeps the default look.
async function dressFor(home) {
  const slug = /^\/b\/([0-9a-f]{10})$/.exec(home)?.[1];
  if (slug === undefined) return;
  let book = null;
  try {
    const response = await fetch(`/book/${slug}.json`, { cache: "no-store" });
    book = response.ok ? await response.json() : null;
  } catch {
    return;
  }
  // Review of 2026-11-17, pass 2 (item 17): the last step offered only the
  // way back; from a book it also starts that book's first puzzle.
  const first = book !== null && typeof book === "object" && Array.isArray(book.puzzles) ? book.puzzles[0] : null;
  const start = document.querySelector("[data-hts-start]");
  if (start !== null && first !== null && typeof first === "object" && /^[0-9a-f]{10}$/.test(first.key ?? "")) {
    start.href = `/play/${first.key}?book=${slug}`;
    start.hidden = false;
    document.querySelector(".hts-end .hts-home-end")?.classList.replace("hts-go", "hts-quiet");
  }
  if (book === null || typeof book !== "object" || typeof book.theme !== "string"
      || !/^[a-z]+$/.test(book.theme)) return;
  // Which themes draw decorations is decor.js's to say, so this page names
  // no theme (it stays generic: AC-E of CARD-419).
  const decor = await import("/decor.js");
  if (!decor.DECORATED_THEMES.includes(book.theme)) return;
  document.documentElement.dataset.theme = book.theme;
  const sheet = document.createElement("link");
  sheet.rel = "stylesheet";
  sheet.href = "/decor.css";
  document.head.append(sheet);
  decor.decorate();
}

function load() {
  const page = document.querySelector("[data-hts-page]");
  if (page === null) return;
  const home = homeHref(document.referrer, window.location.origin);
  dressFor(home);
  for (const link of page.querySelectorAll("[data-hts-home]")) link.setAttribute("href", home);
  const wizard = setupWizard(page);
  const tryBoard = setupTry(page);
  setupSqueeze(page);
  setupAgree(page);
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
