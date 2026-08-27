# User Stories

## Nonogram Generator v1 (2026-08-27)

US-001: As a Puzzle Creator, I want to generate a random black/white grid at
        a chosen size (10x10 to 50x50), so that I have raw material for a
        puzzle without designing one by hand.

US-002: As a Puzzle Creator, I want to pick a picture from a built-in image
        library (cat, house, heart, moon, etc.), so that I can generate a
        recognizable-shape puzzle without drawing one myself.

US-003: As a Puzzle Creator, I want to upload my own image and have it
        converted into a black/white puzzle grid, so that I can turn a
        personal picture into a nonogram.

US-004: As a Puzzle Creator, I want the tool to compute row and column clues
        from any solution grid, so that I get a playable puzzle definition,
        not just a picture.

US-005: As a Puzzle Creator, I want the tool to verify a puzzle has exactly
        one solution before handing it to me, so that I never end up with an
        unsolvable or ambiguous puzzle.

US-006: As a Puzzle Creator, I want random/library-generated puzzles that
        fail the uniqueness check to be regenerated automatically, so that I
        don't have to manually retry until I get a valid one.

US-007: As a Puzzle Creator, when my own uploaded image doesn't yield a
        unique-solution puzzle, I want the tool to try a small automatic
        pixel adjustment before giving up, so that minor ambiguity doesn't
        force me to redo the whole conversion by hand.

US-008: As a Puzzle Creator, I want to choose a difficulty level
        (Easy/Medium/Hard), so that I get puzzles that match how much of a
        challenge I want.

US-009: As a Puzzle Creator, I want to export a finished puzzle as PNG/SVG,
        so that I can print it or use it as an image.

US-010: As a Puzzle Creator, I want to export the underlying grid and clues
        as JSON/CSV, so that I can reuse the puzzle data in another tool or
        app later.

## PDF export with answer key (2026-08-27)

US-011: As a Puzzle Creator, I want every puzzle to have a name (auto-generated
        by default, or one I choose), so that I can tell my puzzles apart
        when I have several saved.

US-012: As a Puzzle Creator, I want to export a puzzle as a single PDF
        containing both the blank puzzle and its answer key, labeled with
        the puzzle's name and difficulty, so that I have one printable file
        with everything needed to solve and check it later.
