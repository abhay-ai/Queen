from mcp.server.fastmcp import FastMCP
import queen

# Create an MCP server named "queen"
mcp = FastMCP("queen")

@mcp.tool()
def validate_move(fen: str, move_uci: str) -> dict:
    """
    Validate a chess move from a given FEN state using the Prolog constraint engine.
    
    Parameters:
    - fen: The FEN string representing the current board state.
    - move_uci: The move in UCI format (e.g. 'e2e4').
    
    Returns:
    A dictionary with keys:
    - "is_legal": boolean indicating whether the move is legal.
    - "explanation": a string explaining the rule violation if the move is illegal.
    """
    is_legal, explanation = queen.check_move_diagnostics(fen, move_uci)
    return {
        "is_legal": is_legal,
        "explanation": explanation
    }

@mcp.tool()
def get_legal_moves(fen: str) -> list[str]:
    """
    Get all legal moves for the given FEN position.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A list of legal moves in UCI format.
    """
    return queen.get_legal_moves(fen)

@mcp.tool()
def get_game_status(fen: str) -> dict:
    """
    Get the game status (active, stalemate, checkmate) for the given FEN position.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A dictionary with keys:
    - "status": the game status ("active", "stalemate", "checkmate", "error").
    - "winner": the winning player ("white", "black") or None.
    """
    return queen.get_game_status(fen)

@mcp.tool()
def get_pinned_pieces(fen: str) -> list[str]:
    """
    Get all pinned friendly pieces for the turn player in the given FEN position.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A list of square coordinates (algebraic notation) containing pinned friendly pieces.
    """
    return queen.get_pinned_pieces(fen)

@mcp.tool()
def get_threats(fen: str) -> dict:
    """
    Get all friendly pieces and defended coordinates under attack by the opponent.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A dictionary with keys:
    - "threatened_pieces": list of friendly pieces currently attacked by opponent.
    - "defended_pieces": list of friendly pieces protected by friendly pieces.
    """
    return {
        "threatened_pieces": queen.get_threatened_pieces(fen),
        "defended_pieces": queen.get_defended_pieces(fen)
    }

@mcp.tool()
def get_discovered_attacks(fen: str) -> list[dict]:
    """
    Get all discovered attack setups in the given FEN position.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A list of candidates with keys: "blocker", "attacker", and "target".
    """
    return queen.get_discovered_attacks(fen)

@mcp.tool()
def get_forks(fen: str) -> dict:
    """
    Get existing forks and moves that create new forks in the given FEN position.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A dictionary with keys:
    - "existing": list of existing forks with keys "forker" and "targets".
    - "moves_creating_forks": list of moves that create new forks, with keys "move" and "targets".
    """
    return queen.get_forks(fen)

@mcp.tool()
def get_tactical_summary(fen: str) -> dict:
    """
    Get a complete tactical overview of the given FEN chess position.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A consolidated dictionary containing:
    - "pinned_pieces": list of pinned pieces.
    - "threatened_pieces": list of attacked pieces.
    - "defended_pieces": list of protected pieces.
    - "discovered_attacks": discovered attack relationships.
    - "forks": active forks and fork-creating moves.
    - "game_status": checkmate, stalemate, or active status.
    """
    return queen.get_tactical_summary(fen)

def main():
    # Start the stdio MCP server
    mcp.run()

if __name__ == "__main__":
    main()
