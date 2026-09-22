# Book rules and admin UI requirements

*Living document — the rules for assembling a book in the admin panel. Updated as books are made. Companion to [book_generation_admin_panel.md](book_generation_admin_panel.md) (Book 1 profile, size × difficulty matrix, print-fit rules BK-1…BK-7).*

## Current workflow (for reference)

| Screen | Route | Today |
|---|---|---|
| New book | `/books` → create | Title, theme, audience |
| Print setup — Step 1 of 4 | `/book/<id>/setup-print` | Trim width / height / unit |
| Puzzle selection — Step 2 of 4 | `/book/<id>/select-puzzles` | Filters (theme, name, difficulty, size range, quality), multi-select tiles, selection counter |
| Arrangement — Step 3 of 4 | `/book/<id>/arrange-puzzles` | Order, titles, delete, page breaks |
| Finalise & export — Step 4 of 4 | `/book/<id>/finalize` | Cover, guide page, PDF |
| Book detail | `/book/<id>` | Details, status & export; links only to Print setup and Puzzle selection |
| Books list | `/books` | Title, theme, audience, puzzle count, pages, status, created |

## 1. Distribution plan (Print setup)

- **BK-UI-1 Plan on Print setup.** The Print setup screen (the second screen, after New book) carries a *general puzzle distribution plan*: total puzzle count and the easy / medium / hard split. Default **150 puzzles, 40% easy / 40% medium / 20% hard** (= 60 / 60 / 30). Both the count and the split are editable; the split must sum to 100%.
- **BK-UI-2 Plan per longest side.** Below the general plan, a rough plan per longest-side bucket (≤15, 16–20, 21–25, 26–30) with an easy / medium / hard count in each cell — e.g. for 21–25: 5 / 15 / 10 in the research matrix. It is prefilled from the Book 1 matrix ([book_generation_admin_panel.md §2](book_generation_admin_panel.md)) rescaled to the book's count and split, rounded so the row and column totals match the general plan; every cell is editable afterwards. The default for 150 × 40/40/20:

  | Longest side | Easy | Medium | Hard | Total |
  |---|---|---|---|---|
  | ≤15 | 20 | 7 | 0 | 27 |
  | 16–20 | 30 | 27 | 6 | 63 |
  | 21–25 | 10 | 20 | 12 | 42 |
  | 26–30 | 0 | 6 | 12 | 18 |
  | **Total** | **60** | **60** | **30** | **150** |

  (The research matrix's own shares sum to 30 / 45 / 25; the example "5 / 15 / 10" for 21–25 is from that matrix, and a 40 / 40 / 20 book rescales it. If the owner edits the general split, the per-bucket plan is re-derived unless the cells were edited by hand, in which case the screen warns that the two disagree.)
- **BK-UI-3 Plan is stored with the book** and survives leaving the workflow; it is the reference for every planned-vs-actual figure below.

## 2. Puzzle selection in four tabs

- **BK-UI-4 One tab per longest side.** Puzzle selection is split into four tabs (or sub-steps) by longest side: **≤15 · 16–20 · 21–25 · 26–30**. The owner can move back and forth between them freely; selections made in one tab are kept when switching.
- **BK-UI-5 Planned vs actual on every tab.** Each tab header and its body show the plan for that bucket and the number selected so far, per difficulty and in total — e.g. `21–25: easy 8 / 10 · medium 20 / 20 · hard 14 / 12`. Over-plan cells are shown as such, not hidden. The same summary for the whole book sits above the tabs.
- **BK-UI-6 Sort order inside a tab.** Puzzles are sorted by **difficulty (easy → medium → hard), then by shorter side ascending** within each difficulty, so the narrow (large-cell) puzzles of a bucket come first. The existing filters (theme, name, quality, difficulty) still apply inside the tab; the size-range filter is replaced by the tab.
- **BK-UI-7 Cell size and floor.** Each tile shows the puzzle's printed cell size on the book's trim, already capped at the 7.5 mm standard cell (BK-1), and is flagged when below the 4.8 mm floor (BK-2).
- **BK-UI-8 Adding puzzles — to be completed.** *(The owner's note ends "When adding puzzles to book, please add a possibility to …" — fill in when known.)*

## 3. Re-entering a book

- **BK-UI-9 Same steps from the book list.** Opening a book from the list lands in the same four-step workflow used at creation. From the book detail page every step is reachable directly — general info (New book fields), Print setup, Puzzle selection (add / remove puzzles), Arrangement, Finalise — regardless of the book's status, except that a *published* book asks for confirmation before puzzles are changed.
- **BK-UI-10 No loss on the way back.** Moving to an earlier step never discards later work: changing the plan keeps the selection (and re-computes planned vs actual); removing a puzzle keeps the rest of the arrangement.

## 4. Books list

- **BK-UI-11 Plan statistics in the list.** The books list shows, per book, **actual puzzles vs planned** (e.g. `132 / 150`) and the easy / medium / hard actual-vs-plan split, plus a status hint when any bucket is short or over. Sorting by "most complete" is available.

## 5. Rules for a book (accumulating)

Rules every book must satisfy before it is marked ready. Add to this list as new ones are learned.

1. Every puzzle has exactly one solution and is not guess-tier (BK-5).
2. Difficulty labels come from the solver's tier, never from grid size.
3. No puzzle prints below the 4.8 mm cell floor on the book's trim without an explicit override (BK-2).
4. No puzzle prints above the 7.5 mm standard cell; the puzzle's top edge sits at the same position on every page (BK-1).
5. Pictures always print upright on a portrait page; no puzzle is turned (BK-3).
6. Actual counts are within ±3 percentage points of the plan in every longest-side × difficulty cell (BK-4).
7. Picture titles appear only in the answer key.
8. Print quality: pure black lines, thin ≥ 0.25 mm, every 5th line twice as heavy; confirmed on printed proof pages (BK-5).
9. The band above a puzzle shows "Puzzle N · Tier", never the picture's title (BK-5).
10. Two small puzzles share a page only at a shared cell ≥ 7.0 mm, only same tier and adjacent in order (BK-6).
11. The book runs easy → medium → hard with a divider page per level (BK-7).

## Open items

- BK-UI-8: the unfinished "possibility to …" when adding puzzles.
- Solution hints: parked as a future feature (not Book 1).
- ~~Tabs as routes or client-side~~ — a detail: a `?bucket=` parameter on the selection route, so browser back/forward works.
- ~~Audience sets the default split~~ — deferred by ADR-0034; the default is 150 at 40/40/20 for now.
- May one puzzle appear in more than one book? Open (ADR-0033); today one book per puzzle.
