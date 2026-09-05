I would not define difficulty using a single metric such as grid size or number of solving steps. Nonogram difficulty is multidimensional. Two 15×15 puzzles can feel completely different: one can be solved almost immediately with basic overlap, while another can require several layers of deduction.

I would build a difficulty profile from several characteristics.

1. The most important metric: solving techniques required

I'd classify the solver's moves into levels.

For example:

Technique	Difficulty
Obvious full line	1
Basic overlap	1
Simple elimination	1
Multiple-line propagation	2
Edge/block interaction	2
Gap restrictions	3
Multiple candidate patterns	3
Advanced overlap	4
Contradiction / assumption	5
Guessing / backtracking	6

Then a puzzle might get a profile like:

Techniques: 1, 1, 2, 2, 3 → Medium

versus:

Techniques: 1, 2, 3, 3, 4, 4 → Hard

This is much more meaningful than "the solver needed 847 operations."

2. Maximum technique required

I'd track:

max_technique

This can be extremely useful.

For example:

Puzzle A

Basic overlap
Simple elimination
Propagation

→ max = 2

Puzzle B

Basic overlap
Propagation
Advanced overlap

→ max = 4

Even if B has fewer solving steps, it is probably perceived as harder.

So I'd make this one of our primary difficulty indicators.

3. Technique distribution

Maximum technique alone isn't enough.

Imagine:

Puzzle A
95% easy moves
5% advanced move
Puzzle B
40% easy
30% medium
30% advanced

Both have max_technique = 4.

But B probably feels considerably harder.

So I'd record something like:

technique_histogram = {
    basic: 42,
    intermediate: 18,
    advanced: 12
}

This could become very useful later.

4. Branching / ambiguity

This is another metric I'd definitely add.

At every solving point, ask:

How many possible placements remain?

Suppose the puzzle reaches a state where:

Line A → 1 possible pattern
Line B → 2 possible patterns
Line C → 7 possible patterns
Line D → 12 possible patterns

Puzzle D has much higher ambiguity.

We could measure:

Average candidate count

and

Maximum candidate count

This gives us an indication of how "open" or constrained the puzzle is.

5. Information gain per move

This one is particularly interesting.

Suppose a move determines:

█████

and immediately allows 15 other cells to be determined.

That's a high-information move.

Another move might determine one cell and nothing else.

So we can calculate something like:

Average cells eliminated/determined per logical deduction

A puzzle where every deduction unlocks lots of information may feel easier, even if it takes many steps.

A puzzle where deductions produce very little information can feel harder.

6. Forcedness / freedom

Related to the previous point.

At each stage we can calculate:

How many legal configurations remain?

For example:

Start
↓
10,000 possible configurations
↓
2,000
↓
300
↓
50
↓
8
↓
1

versus:

Start
↓
10,000
↓
9,000
↓
8,200
↓
6,500
↓
...
↓
1

The second puzzle has much slower information reduction.

That could be a useful measure of perceived difficulty.

7. Backtracking depth

Even if we ultimately require zero guessing, I would still calculate this.

Run a generic search solver and record:

number of branches
maximum branch depth
number of contradictions
number of explored states

For example:

Puzzle A
branches = 0

Excellent.

Puzzle B
branches = 0
search states = 3

Still easy.

Puzzle C
branches = 47
max depth = 6

Probably difficult.

This becomes especially useful for rejecting bad puzzles.

8. "Human solvability" vs mathematical solvability

This distinction is very important.

A puzzle can have:

exactly one solution

but still be horrible for a human.

For example, the only solution might be discoverable through enormous brute force.

We should therefore have two separate properties:

Mathematical validity
unique_solution = true
Human logical solvability
solvable_without_guessing = true

And ideally:

solving_techniques = {...}

This gives us a much stronger quality filter.

9. Dependency depth

Here's another metric I'd experiment with.

Imagine:

A → B → C → D → E

Meaning:

A deduction enables B, B enables C, etc.

That's a deep dependency chain.

Compare:

A → B
A → C
A → D
A → E

The second puzzle has lots of parallel deductions.

The first may feel more like a puzzle because you need to discover a sequence.

So:

dependency_depth

could be a very interesting difficulty feature.

10. Bottlenecks

I'd also detect moments where:

Almost nothing can progress until one particular deduction is made.

For example:

Puzzle progress

████████████████
████████████████
████████████████
███████░░░░░░░░
███████░░░░░░░░

Then one deduction unlocks a large portion of the puzzle.

These "bottlenecks" are often what makes a puzzle feel challenging.

We could record:

number of bottlenecks
size of bottleneck
depth of bottleneck
cells unlocked afterward
11. Clue density

This is simpler, but still useful.

For a 15×15 puzzle:

15 × 15 = 225 cells

We can calculate:

filled cells
empty cells
number of clues
average clue length
maximum clue length
clue density

For example:

███████████████
█░░░░░░░░░░░░░█
█░███████░░░░░█
█░░░░░░░░░░░░░█

versus a very sparse image.

However, I'd treat this as a secondary feature, because image density doesn't directly equal logical difficulty.

12. Symmetry

This is not really difficulty, but it's useful for puzzle quality.

Measure:

horizontal symmetry
vertical symmetry
rotational symmetry
approximate symmetry

Highly symmetrical images can sometimes produce repetitive clues and easier solving.

But we shouldn't automatically reject symmetry.

For some themed books, symmetry could actually be aesthetically desirable.

13. Image complexity

Again, not exactly difficulty.

But I'd record:

Connected components

How many separate objects are there?

🐱

→ 1 component

versus:

🐱 🌳 🏠 ☀️

→ several components.

Also:

number of filled regions
perimeter/area ratio
holes
isolated cells
thin structures
long structures
density variation

This helps us create good pictures, not just difficult puzzles.

14. I would actually separate three concepts

This is important enough that I'd put it into our data model.

A. Difficulty

How difficult is it to solve?

B. Complexity

How complicated is the underlying picture/grid?

C. Quality

Is it an interesting, elegant puzzle?

These are not the same.

For example:

Puzzle	Difficulty	Image complexity	Quality
Cat	Easy	Low	⭐⭐⭐⭐⭐
Castle	Medium	Medium	⭐⭐⭐⭐⭐
Dragon	Easy	High	⭐⭐⭐
Abstract blob	Hard	High	⭐

We don't want to accidentally publish the "hardest" puzzles if they're ugly.

15. I'd create a difficulty vector

Rather than immediately producing:

Difficulty = 7.4

I'd initially store something like:

Puzzle #042

grid:              15 × 15

logical_steps:     87
max_technique:     3
advanced_moves:    8
candidate_peak:    6
branching:         0
dependency_depth:  9
bottlenecks:       2
cells_per_move:    2.8
clue_density:      0.42
image_complexity:  0.61

Then we can derive a human-friendly label:

★★★☆☆ Medium