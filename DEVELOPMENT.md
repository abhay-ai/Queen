# Queen Development & AI Maintenance Guide

This project combines a **SWI-Prolog constraint engine** with a **Python MCP server / library** and a **browser-compatible Tau Prolog client**. 

To maintain compatibility between the native SWI-Prolog implementation and the browser-based client, follow the guidelines below.

---

## 🚀 The Compilation Pipeline

The browser-based interactive playground in `docs/index.html` runs Prolog directly in JavaScript using [Tau Prolog](http://tau-prolog.org/). 

Since SWI-Prolog and Tau Prolog have minor compatibility differences, we use a compilation script to build the browser engine:

### How to Compile `queen.pl` for the Browser
Whenever you make changes to `queen.pl`, compile the updated rules into JavaScript by running:

```bash
python3 convert_prolog.py
```

This will automatically read `queen.pl`, apply compatibility replacements, and output the updated rules and JS bridge code to `docs/queen_engine.js`.

---

## ⚖️ Prolog Writing Guidelines (AI & Developer Rules)

Any AI assistant or human developer making changes to `queen.pl` **must** adhere to the following constraints to ensure the code compiles and runs successfully in the browser:

### 1. Supported Built-ins (ISO Prolog)
Tau Prolog is an ISO-compliant interpreter. You can freely use all standard ISO predicates and constructs:
- **Lists**: `member/2`, `select/3`, `append/3`, `length/2`.
- **Logic / Control**: Cuts (`!`), negation by failure (`\+`), if-then-else (`Condition -> Then ; Else`), disjunctions (`;`).
- **Meta-predicates**: `findall/3`, `once/1`.
- **Arithmetic**: `is/2`, equality/comparison (`=:=`, `=\=`, `<`, `>`, `=<`, `>=`), math functions (like `abs/1`).

### 2. Forbidden SWI-Prolog Built-ins
Avoid using SWI-Prolog-specific built-in predicates that do not exist in the ISO standard. Specifically:
- **Do NOT use `between/3`** directly. Use `queen_between/3` instead (or rely on `convert_prolog.py` to rewrite it).
- **Do NOT use `sum_list/2`** directly. Use `queen_sum_list/2` instead (or rely on `convert_prolog.py` to rewrite it).
- **Do NOT use `memberchk/2`** (use `member/2` with a cut instead).
- **Do NOT use complex library imports** (like `library(clpfd)`, `library(assoc)`, or `library(rbtrees)`). Only standard list manipulation is supported in the browser.

### 3. Shims & Replacements
If you need to introduce new non-standard predicates or complex functions:
1. Implement them as custom pure Prolog predicates directly inside `queen.pl`.
2. Or, if they require different syntax in SWI vs. Tau Prolog, add a string replacement pattern in `convert_prolog.py` to shim them automatically during build time.

---

## 🔌 JavaScript Bridge API

The compiled `docs/queen_engine.js` file exposes the following asynchronous functions to the chessboard UI:

- **`jsCheckMoveDiagnostics(fen, moveUci, callback)`**:
  Validates a move using coordinates and board state. 
  - `callback(isLegal, explanation)`
- **`jsGetLegalMoves(fen, callback)`**:
  Retrieves a sorted list of all legal moves in UCI format (e.g. `['e2e4', 'g1f3']`).
  - `callback(movesList)`
- **`jsGetTacticalSummary(fen, callback)`**:
  Aggregates checks, pins, discovered attacks, material values, and advantage metrics.
  - `callback(summaryObject, error)`

---

## 🧪 Verification Checklist

After editing `queen.pl` and running `convert_prolog.py`, verify the changes by running local python tests:

1. **Verify Python tests pass**:
   ```bash
   python3 -m unittest test_referee.py  # Run from parent directory
   ```
2. **Verify Browser rendering**:
   Open `docs/index.html` in a web browser, make a few moves, select different scenarios, and verify that the console contains no Prolog syntax or resolution errors.

---

## 📜 History of Key Maintenance Tasks (AI Memory & Reference)

Use this section as a reference for issues that have been solved to avoid re-introducing regression bugs.

### 1. Live FEN Sandbox Chessboard Rendering Failure (May 2026)
* **Problem**: The interactive chessboard and analysis tabs remained empty on FEN input.
* **Root Causes**:
  1. **Concurrency Aborts**: The JS wrapper invoked `plSession.answers()` concurrently, causing query state machine aborts in Tau Prolog.
  2. **Existence Errors**: JS bridge queried predicates (`checkmate/2`, `stalemate/2`, `is_fork/4`, `delete/3`) that did not exist in the Prolog module or library.
  3. **Backtracking Timeout**: Capped at 10,000 inferences in-browser, the engine exceeded the limit due to $O(64 \times 64)$ backtracking in `legal_move/4` where coordinate generators ran before occupancy checks.
* **Solutions**:
  - Reordered subgoals in `legal_move/4` to bind variables up-front via `occupied(...)` before running coordinate generators.
  - Increased Tau Prolog session limit to `1,000,000`.
  - Refactored JS bridge to run a single consolidated query `js_tactical_summary/14` via `plSession.answer` (singular) to eliminate asynchronous concurrency corruption.

### 2. Geometric Constraints Optimization (May 2026)
* **Problem**: Even after checkmate optimization, the tactical search took up to 9 seconds on some positions.
* **Solutions**:
  - **`aligned/5` check**: Added a geometric alignment filter for sliding pieces. If a target square is ground, we compute the ray direction instantly instead of backtracking through all 8 vectors.
  - **`candidate_target/4`**: Added a custom occupancy-aware target generator for sliders that stops walking a ray as soon as a blocking piece is encountered.
  - **Discovered Attack filter**: Added `aligned` checks to filter blockers strictly to the line of sight between the slider and the target, avoiding $O(\text{pieces})$ select/move checks.

### 3. Defended Pieces Bug & Variable Name Collision (May 2026)
* **Problem**: Defended pieces were not being listed for sliding defenders, and forks returned an empty list `[]` under checkmate.
* **Root Causes**:
  - **`is_defended` Occupancy**: The friendly piece being defended was not removed from the simulated `TempBoard` before placing the simulated opponent piece, causing `\+ occupied` validation to fail.
  - **Variable Collision**: In `js_tactical_summary`, the variable `Status` was bound by the game status query (e.g., `checkmate`), causing the subsequent forks findall query to fail.
* **Solutions**:
  - Fixed `is_defended/3` to select and remove the friendly piece first.
  - Renamed the findall variable inside `js_tactical_summary` to `ForkStatus`.

### 4. Fork safety classification (May 2026)
* **Problem**: The pure geometric fork finder resulted in combinatoric explosion (e.g. 6 forks for one queen) and returned unsafe forks.
* **Solution**:
  - Added `fork_status/6` to classify forks into:
    - `winning_fork`: Attacker is safe/defended, target undefended.
    - `winning_trade`: Both targets defended, but capturing one wins material.
    - `winning_sacrifice`: Attacker is hanging, but one target has higher value.
    - `defended_trade` / `unsafe_attacker_hangs`: Neutral or unfavorable.
  - Updated python `queen.py` and JS `queen_engine.js` to parse and output this status.

