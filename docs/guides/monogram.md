Nonograms generation

Generate a random black/white grid
e.g. 10×10, 15×15, 20×20.
Calculate the clues automatically from the grid.
Example: ██·███·· → 2 3.
Verify that the puzzle is solvable
Ideally, the clues should lead to exactly one solution.
Control difficulty
We can generate puzzles that are easy, medium, or hard.
Export the puzzle
PNG/SVG for printing or an image.
We can also export the underlying grid and clues as JSON/CSV.
Optionally, we can generate a specific picture — for example, a cat, house, heart, moon, etc. — and convert it into a valid Nonogram.
The interesting part: uniqueness

Simply generating a random grid and calculating clues does not guarantee a good Nonogram. The clues might have multiple possible solutions.

So I'd build a small solver:

Generate solution grid
        ↓
Calculate row + column clues
        ↓
Run Nonogram solver
        ↓
How many solutions?
   ┌────┴────┐
   1         >1
   ↓          ↓
 Keep       Generate again

For example, we could start with a 10×10 generator and make something like:

      1 1 3 2 1
      1 3 1 2 1
    ┌───────────
  1 │ · · █ · ·
  2 │ · █ █ █ ·
  1 │ · · █ · ·
  3 │ █ █ · █ █
  1 │ · · · █ ·

