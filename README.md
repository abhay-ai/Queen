# Queen 👑

Queen is a hybrid Chess analysis and validation system. It combines the declarative power of a **Prolog constraint engine** with a **Python bridge** and exposes it as a **Model Context Protocol (MCP) server** for AI/LLM integration.

## Project Structure

- `queen.pl`: The core SWI-Prolog rulebase defining chess legal moves, piece interactions, pins, threats, checks, forks, discovered attacks, and game states.
- `queen.py`: The Python bridge that parses FEN board states into symbolic Prolog variables, queries the Prolog engine via `pyswip`, and computes tactical summaries (including material counts and dynamic advantages).
- `queen_mcp.py`: A FastMCP server that exposes these analysis and validation tools as MCP tools using the stdio transport.

## Prerequisites

- **Python 3.10+**
- **SWI-Prolog**: Ensure `swipl` is installed and in your system PATH.
- **Python Packages**:
  ```bash
  pip install pyswip python-chess mcp
  ```

## Features & MCP Tools

Queen exposes the following tools:

1. **`validate_move(fen, move_uci)`**: Uses Prolog constraint rules to validate a move and provides a detailed explanation if it's illegal.
2. **`get_legal_moves(fen)`**: Lists all legal moves from the current position.
3. **`get_game_status(fen)`**: Checks if the game is active, checkmate, or stalemate, and identifies the winner.
4. **`get_pinned_pieces(fen)`**: Identifies friendly pieces pinned to the king.
5. **`get_threats(fen)`**: Lists friendly pieces under attack and friendly pieces defending each other.
6. **`get_discovered_attacks(fen)`**: Identifies candidate blockers whose movement opens an attack line.
7. **`get_forks(fen)`**: Finds active forks and moves that create new forks.
8. **`get_tactical_summary(fen)`**: Combines all tactical details into a single rich analysis payload.

## Running the MCP Server

You can run the MCP server directly using Python:

```bash
python queen_mcp.py
```

To configure it in your MCP host (like Claude Desktop), add it to your configuration file:

```json
{
  "mcpServers": {
    "queen": {
      "command": "python",
      "args": ["/absolute/path/to/Queen/queen_mcp.py"]
    }
  }
}
```
