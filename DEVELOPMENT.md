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
