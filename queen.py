import os
from pyswip import Prolog

prolog = Prolog()
# Consult queen.pl relative to this script's path
current_dir = os.path.dirname(os.path.abspath(__file__))
chess_pl_path = os.path.join(current_dir, "queen.pl")
prolog.consult(chess_pl_path)

file_map = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8}
file_map_inv = {v: k for k, v in file_map.items()}

def parse_fen_row(rank_idx, rank_str, piece_map):
    prolog_rank = 8 - rank_idx
    expanded_row = "".join(["_" * int(c) if c.isdigit() else c for c in rank_str])
    return [
        f"piece({'white' if char.isupper() else 'black'}, {piece_map[char.lower()]}, {file_idx}-{prolog_rank})"
        for file_idx, char in enumerate(expanded_row, start=1)
        if char != "_"
    ]

def parse_fen_to_prolog_vars(fen):
    """
    Parses a FEN string into components ready for Prolog state assertion.
    Gracefully handles partial FEN strings (e.g., when the LLM omits the metadata suffix).
    """
    try:
        piece_map = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'}
        parts = fen.split()
        if not parts:
            return None
            
        ranks = parts[0].split('/')
        prolog_pieces = [p for r_idx, r_str in enumerate(ranks) for p in parse_fen_row(r_idx, r_str, piece_map)]
        prolog_board = "[" + ",".join(prolog_pieces) + "]"
        
        # Default to white if turn color is missing
        turn_color = "white"
        if len(parts) > 1:
            turn_color = "white" if parts[1] == "w" else "black"
            
        # Default to no castling rights if missing
        prolog_rights = "[]"
        if len(parts) > 2:
            rights = [('wk' if 'K' in parts[2] else ''), ('wq' if 'Q' in parts[2] else ''), ('bk' if 'k' in parts[2] else ''), ('bq' if 'q' in parts[2] else '')]
            prolog_rights = "[" + ",".join([r for r in rights if r]) + "]"
            
        # Default to no en passant if missing
        ep_file = "none"
        if len(parts) > 3 and parts[3] != '-':
            if parts[3][0] in file_map:
                ep_file = file_map[parts[3][0]]
        
        return prolog_board, turn_color, prolog_rights, ep_file
    except Exception as e:
        print(f"Error parsing FEN '{fen}': {e}")
        return None

def check_move_diagnostics(fen, move_uci):
    """
    Queries Prolog to validate the move using symbolic rules. 
    Returns a tuple: (is_legal, explanation_string)
    """
    if not isinstance(move_uci, str) or len(move_uci) < 4 or len(move_uci) > 5:
        return False, "Malformed string format. It must be exactly 4 lowercase characters (e.g., e2e4)."

    move_from, move_to = move_uci[:2], move_uci[2:4]
    
    if move_from[0] not in file_map or not move_from[1].isdigit() or move_to[0] not in file_map or not move_to[1].isdigit():
        return False, "Coordinates fall entirely outside the boundaries of an 8x8 chessboard grid."

    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return False, "Invalid FEN board state."
        
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    pl_from = f"{file_map[move_from[0]]}-{move_from[1]}"
    pl_to = f"{file_map[move_to[0]]}-{move_to[1]}"
    
    # Declarative Metarational Query targeting Prolog's Explanation variable
    query_string = f"validate_and_explain(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), {pl_from}, {pl_to}, Explanation)"
    
    try:
        results = list(prolog.query(query_string))
        if results:
            explanation = results[0]['Explanation']
            if isinstance(explanation, bytes):
                explanation = explanation.decode('utf-8')
                
            if explanation == "SUCCESS":
                return True, ""
            else:
                import re
                def replace_match(match):
                    x = int(match.group(1))
                    y = int(match.group(2))
                    file_char = file_map_inv.get(x, str(x))
                    return f"{file_char}{y}"
                explanation = re.sub(r'\b([1-8])-([1-8])\b', replace_match, explanation)
                return False, explanation
                
        return False, "Move rejected by core constraint engine."
    except Exception as e:
        return False, f"Symbolic constraints exception: {e}"

def get_legal_moves(fen: str) -> list[str]:
    """
    Find all legal moves from the current position.
    
    Parameters:
    - fen: The FEN string representing the current board state.
    
    Returns:
    A list of legal moves in UCI format (e.g. ['e2e4', 'g1f3']).
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
        
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    query_string = f"legal_move(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), FromX-FromY, ToX-ToY, _)"
    
    try:
        import chess
        board = chess.Board(fen)
        results = list(prolog.query(query_string))
        moves = []
        for r in results:
            from_x = r['FromX']
            from_y = r['FromY']
            to_x = r['ToX']
            to_y = r['ToY']
            
            # Check if this is a pawn moving to the promotion rank (8 for white, 1 for black)
            from_square = chess.square(from_x - 1, from_y - 1)
            piece = board.piece_at(from_square)
            if piece and piece.piece_type == chess.PAWN and (to_y == 8 or to_y == 1):
                for promo in ['q', 'r', 'b', 'n']:
                    moves.append(f"{file_map_inv[from_x]}{from_y}{file_map_inv[to_x]}{to_y}{promo}")
            else:
                moves.append(f"{file_map_inv[from_x]}{from_y}{file_map_inv[to_x]}{to_y}")
        # Return unique, sorted moves
        return sorted(list(set(moves)))
    except Exception as e:
        print(f"Error querying legal moves: {e}")
        return []

def get_game_status(fen: str) -> dict:
    """
    Get the game status (active, stalemate, checkmate) for the given position.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A dictionary with keys "status" ("active", "checkmate", "stalemate", "error") and "winner" ("white", "black", or None).
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return {"status": "error", "winner": None}
        
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    query_string = f"game_status(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), status(StatusType, Winner))"
    
    try:
        results = list(prolog.query(query_string))
        if results:
            status_type = results[0]['StatusType']
            winner = results[0]['Winner']
            
            if isinstance(status_type, bytes):
                status_type = status_type.decode('utf-8')
            if isinstance(winner, bytes):
                winner = winner.decode('utf-8')
                
            return {
                "status": str(status_type),
                "winner": str(winner) if winner != 'none' else None
            }
        return {"status": "active", "winner": None}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_pinned_pieces(fen: str) -> list[dict]:
    """
    Find all pinned friendly pieces for the turn player. Pinned pieces cannot move
    without exposing their King to check.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A list of pinned pieces, where each piece is a dictionary:
    {"piece": "pawn"|"knight"|..., "square": "e4"}
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, _, _ = state_vars
    query_string = f"member(piece({turn_color}, Type, X-Y), {prolog_board}), is_pinned({prolog_board}, {turn_color}, X-Y)"
    try:
        results = list(prolog.query(query_string))
        pinned = []
        for r in results:
            piece_type = r['Type']
            if isinstance(piece_type, bytes):
                piece_type = piece_type.decode('utf-8')
            pinned.append({
                "piece": str(piece_type),
                "square": f"{file_map_inv[r['X']]}{r['Y']}"
            })
        seen = set()
        unique_pinned = []
        for p in pinned:
            key = (p['piece'], p['square'])
            if key not in seen:
                seen.add(key)
                unique_pinned.append(p)
        return unique_pinned
    except Exception as e:
        print(f"Error querying pinned pieces: {e}")
        return []

def get_threatened_pieces(fen: str) -> list[dict]:
    """
    Find all friendly pieces that are currently under attack by the opponent.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A list of threatened pieces, where each piece is a dictionary:
    {"piece": "pawn"|"knight"|..., "square": "e4"}
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, _, _ = state_vars
    query_string = f"member(piece({turn_color}, Type, X-Y), {prolog_board}), is_attacked({prolog_board}, {turn_color}, X-Y)"
    try:
        results = list(prolog.query(query_string))
        threats = []
        for r in results:
            piece_type = r['Type']
            if isinstance(piece_type, bytes):
                piece_type = piece_type.decode('utf-8')
            threats.append({
                "piece": str(piece_type),
                "square": f"{file_map_inv[r['X']]}{r['Y']}"
            })
        seen = set()
        unique_threats = []
        for t in threats:
            key = (t['piece'], t['square'])
            if key not in seen:
                seen.add(key)
                unique_threats.append(t)
        return unique_threats
    except Exception as e:
        print(f"Error querying threatened pieces: {e}")
        return []

def get_defended_pieces(fen: str) -> list[dict]:
    """
    Find all friendly pieces that are currently defended by other friendly pieces.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A list of defended pieces, where each piece is a dictionary:
    {"piece": "pawn"|"knight"|..., "square": "e4"}
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, _, _ = state_vars
    query_string = f"member(piece({turn_color}, Type, X-Y), {prolog_board}), is_defended({prolog_board}, {turn_color}, X-Y)"
    try:
        results = list(prolog.query(query_string))
        defended = []
        for r in results:
            piece_type = r['Type']
            if isinstance(piece_type, bytes):
                piece_type = piece_type.decode('utf-8')
            defended.append({
                "piece": str(piece_type),
                "square": f"{file_map_inv[r['X']]}{r['Y']}"
            })
        seen = set()
        unique_defended = []
        for d in defended:
            key = (d['piece'], d['square'])
            if key not in seen:
                seen.add(key)
                unique_defended.append(d)
        return unique_defended
    except Exception as e:
        print(f"Error querying defended pieces: {e}")
        return []

def get_discovered_attacks(fen: str) -> list[dict]:
    """
    Find discovered attack setups, where moving a friendly blocker piece opens a line
    of attack from a friendly slider onto an enemy target.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A list of discovered attack dicts:
    {"blocker": "d4", "attacker": "a1", "target": "a8"}
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, _, _ = state_vars
    query_string = f"discovered_attack_candidate({prolog_board}, {turn_color}, BlockerX-BlockerY, AttackerX-AttackerY, TargetX-TargetY)"
    try:
        results = list(prolog.query(query_string))
        candidates = []
        for r in results:
            candidates.append({
                "blocker": f"{file_map_inv[r['BlockerX']]}{r['BlockerY']}",
                "attacker": f"{file_map_inv[r['AttackerX']]}{r['AttackerY']}",
                "target": f"{file_map_inv[r['TargetX']]}{r['TargetY']}"
            })
        seen = set()
        unique_candidates = []
        for c in candidates:
            key = (c['blocker'], c['attacker'], c['target'])
            if key not in seen:
                seen.add(key)
                unique_candidates.append(c)
        return unique_candidates
    except Exception as e:
        print(f"Error querying discovered attacks: {e}")
        return []

def get_forks(fen: str) -> dict:
    """
    Find existing forks (one piece attacking two enemy pieces) and moves that can create new forks.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A dictionary with keys:
    - "existing": list of existing forks: [{"forker": "c7", "targets": ["a8", "e8"]}]
    - "moves_creating_forks": list of fork-creating moves: [{"move": "d5c7", "targets": ["a8", "e8"]}]
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return {"existing": [], "moves_creating_forks": []}
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    
    # 1. Existing forks
    forks_query = f"is_fork({prolog_board}, {turn_color}, ForkerX-ForkerY, Target1X-Target1Y, Target2X-Target2Y), fork_status({prolog_board}, {turn_color}, ForkerX-ForkerY, Target1X-Target1Y, Target2X-Target2Y, Status)"
    existing_forks = []
    try:
        results = list(prolog.query(forks_query))
        for r in results:
            status = r['Status']
            if isinstance(status, bytes):
                status = status.decode('utf-8')
            existing_forks.append({
                "forker": f"{file_map_inv[r['ForkerX']]}{r['ForkerY']}",
                "targets": [
                    f"{file_map_inv[r['Target1X']]}{r['Target1Y']}",
                    f"{file_map_inv[r['Target2X']]}{r['Target2Y']}"
                ],
                "status": status
            })
    except Exception as e:
        print(f"Error querying existing forks: {e}")
        
    seen = set()
    unique_existing = []
    for f in existing_forks:
        key = (f['forker'], tuple(sorted(f['targets'])))
        if key not in seen:
            seen.add(key)
            unique_existing.append(f)
            
    # 2. Moves creating forks
    creates_fork_query = f"creates_fork(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), FromX-FromY, ToX-ToY, Target1X-Target1Y, Target2X-Target2Y)"
    moves_creating = []
    try:
        results = list(prolog.query(creates_fork_query))
        for r in results:
            moves_creating.append({
                "move": f"{file_map_inv[r['FromX']]}{r['FromY']}{file_map_inv[r['ToX']]}{r['ToY']}",
                "targets": [
                    f"{file_map_inv[r['Target1X']]}{r['Target1Y']}",
                    f"{file_map_inv[r['Target2X']]}{r['Target2Y']}"
                ]
            })
    except Exception as e:
        print(f"Error querying fork-creating moves: {e}")
        
    seen_creates = set()
    unique_creates = []
    for m in moves_creating:
        key = (m['move'], tuple(sorted(m['targets'])))
        if key not in seen_creates:
            seen_creates.add(key)
            unique_creates.append(m)
            
    return {
        "existing": unique_existing,
        "moves_creating_forks": unique_creates
    }

def get_checking_pieces(board) -> list[dict]:
    import chess
    checking_pieces = []
    if board.is_check():
        for sq in board.checkers():
            p = board.piece_at(sq)
            checking_pieces.append({
                "piece": p.symbol() if p else "unknown",
                "square": chess.square_name(sq)
            })
    return checking_pieces

def get_moves_giving_check(board) -> list[str]:
    return [move.uci() for move in board.legal_moves if board.gives_check(move)]

def get_moves_creating_pins(board) -> list[dict]:
    import chess
    opp_color = not board.turn
    existing_pins = set()
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.color == opp_color and p.piece_type != chess.KING:
            if board.is_pinned(opp_color, sq):
                existing_pins.add(chess.square_name(sq))
                
    moves_creating = []
    for move in board.legal_moves:
        board.push(move)
        current_opp_color = board.turn
        new_pins = []
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if p and p.color == current_opp_color and p.piece_type != chess.KING:
                sq_name = chess.square_name(sq)
                if board.is_pinned(current_opp_color, sq) and sq_name not in existing_pins:
                    new_pins.append(sq_name)
        if new_pins:
            moves_creating.append({
                "move": move.uci(),
                "pinned_pieces": new_pins
            })
        board.pop()
    return moves_creating

def get_moves_creating_attacks(board) -> list[dict]:
    import chess
    opp_color = not board.turn
    attacks_created = []
    for move in board.legal_moves:
        if board.is_capture(move):
            continue
        board.push(move)
        to_square = move.to_square
        attacked_squares = board.attacks(to_square)
        new_attacks = []
        for sq in attacked_squares:
            opp_piece = board.piece_at(sq)
            if opp_piece and opp_piece.color == opp_color:
                is_high_value = opp_piece.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
                is_defended = bool(board.attackers(opp_color, sq))
                if is_high_value or not is_defended:
                    new_attacks.append({
                        "piece": opp_piece.symbol(),
                        "square": chess.square_name(sq)
                    })
        if new_attacks:
            attacks_created.append({
                "move": move.uci(),
                "attacks": new_attacks
            })
        board.pop()
    return attacks_created

def get_tactical_summary(fen: str) -> dict:
    """
    Get a consolidated tactical summary of the board position (pins, threats, defense, forks, check status, and multi-step tactics).
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A summary dictionary.
    """
    import chess
    try:
        board = chess.Board(fen)
    except Exception as e:
        return {"error": f"Invalid FEN board state: {e}"}
        
    try:
        threatened = get_threatened_pieces(fen)
        in_check = board.is_check()
        return {
            "pinned_pieces": get_pinned_pieces(fen),
            "threatened_pieces": threatened,
            "defended_pieces": get_defended_pieces(fen),
            "discovered_attacks": get_discovered_attacks(fen),
            "forks": get_forks(fen),
            "game_status": get_game_status(fen),
            "in_check": in_check,
            "checking_pieces": get_checking_pieces(board),
            "mate_in_one": get_mate_in_one(fen),
            "mate_in_two": get_mate_in_two(fen),
            "mate_in_three": get_mate_in_three(fen),
            "forced_material_wins": get_forced_material_wins(fen),
            "moves_giving_check": get_moves_giving_check(board),
            "moves_creating_pins": get_moves_creating_pins(board),
            "moves_creating_attacks": get_moves_creating_attacks(board)
        }
    except Exception as e:
        return {"error": f"Error generating tactical summary: {e}"}


def convert_san_to_uci(fen: str, move_san: str) -> str:
    """
    Utility tool for LLM to convert a Standard Algebraic Notation (SAN) chess move 
    (e.g., 'Nf3', 'c6', 'exd5', 'O-O') to its legal UCI coordinate notation (e.g., 'g1f3', 'c7c6').
    
    Parameters:
    - fen: The current FEN board state.
    - move_san: The move string in standard algebraic notation.
    
    Returns:
    The parsed UCI coordinate move if legal and recognized, otherwise an error description.
    """
    import chess
    try:
        board = chess.Board(fen)
        san_candidate = move_san.strip()
        
        # Normalize castling codes
        if san_candidate.lower() in ('o-o', '0-0'):
            san_candidate = 'O-O'
        elif san_candidate.lower() in ('o-o-o', '0-0-0'):
            san_candidate = 'O-O-O'
            
        candidates = [san_candidate]
        # Normalize starting letter capitalization (e.g. nf3 -> Nf3)
        if len(san_candidate) >= 2 and san_candidate[0] in ('n', 'b', 'r', 'q', 'k'):
            candidates.append(san_candidate[0].upper() + san_candidate[1:])
            
        parsed_move = None
        for cand in candidates:
            try:
                parsed_move = board.parse_san(cand)
                break
            except Exception:
                pass
                
        if parsed_move:
            return parsed_move.uci()
        else:
            return f"Error: Move '{move_san}' is not recognized as a legal algebraic move in this position."
    except Exception as e:
        return f"Error parsing move: {e}"

def convert_uci_to_san(fen: str, move_uci: str) -> str:
    """
    Utility tool for LLM to convert a UCI coordinate notation chess move (e.g., 'g1f3', 'e1g1')
    to its Standard Algebraic Notation (SAN) representation (e.g., 'Nf3', 'O-O').
    
    Parameters:
    - fen: The current FEN board state.
    - move_uci: The move string in standard UCI coordinate notation.
    
    Returns:
    The parsed algebraic (SAN) move if legal and recognized, otherwise an error description.
    """
    import chess
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci.strip().lower())
        if move in board.legal_moves:
            return board.san(move)
        else:
            return f"Error: Move '{move_uci}' is not a legal move in this position."
    except Exception as e:
        return f"Error parsing move: {e}"

def simulate_move(fen: str, move: str) -> dict:
    """
    Simulates playing a move (either UCI coordinate or algebraic notation) on the current FEN board state
    and returns the resulting FEN of the board after the move is played.
    
    This allows you to see the consequences of a candidate move by querying the resulting FEN
    with other analytical tools (e.g. get_threatened_pieces, get_pinned_pieces) to check for opponent counters.
    
    Parameters:
    - fen: The current FEN board state.
    - move: The move coordinates or algebraic notation (e.g. 'e2e4', 'Nf3').
    
    Returns:
    A dictionary containing:
    - 'resulting_fen': The FEN string after the move is played.
    - 'is_legal': Boolean indicating if the move was legal.
    - 'error': Optional error description.
    """
    import chess
    import re
    try:
        board = chess.Board(fen)
        parsed_move = None
        clean_move = move.strip()
        if re.match(r'^[a-h][1-8][a-h][1-8][qrbn]?$', clean_move.lower()):
            parsed_move = chess.Move.from_uci(clean_move.lower())
        else:
            san_candidate = clean_move
            if san_candidate.lower() in ('o-o', '0-0'):
                san_candidate = 'O-O'
            elif san_candidate.lower() in ('o-o-o', '0-0-0'):
                san_candidate = 'O-O-O'
            
            candidates = [san_candidate]
            if len(san_candidate) >= 2 and san_candidate[0] in ('n', 'b', 'r', 'q', 'k'):
                candidates.append(san_candidate[0].upper() + san_candidate[1:])
            
            for cand in candidates:
                try:
                    parsed_move = board.parse_san(cand)
                    break
                except Exception:
                    pass
        
        if parsed_move and parsed_move in board.legal_moves:
            board.push(parsed_move)
            return {
                'resulting_fen': board.fen(),
                'is_legal': True,
                'error': None
            }
        else:
            return {
                'resulting_fen': None,
                'is_legal': False,
                'error': f"Move '{move}' is not a legal move in this position."
            }
    except Exception as e:
        return {
            'resulting_fen': None,
            'is_legal': False,
            'error': f"Error simulating move: {e}"
        }

def get_material_status(fen: str) -> dict:
    """
    Get the material count and pieces lost for both sides from the given FEN.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A dictionary containing:
    - 'white_lost': {'pawn': W_P, 'knight': W_N, 'bishop': W_B, 'rook': W_R, 'queen': W_Q}
    - 'black_lost': {'pawn': B_P, 'knight': B_N, 'bishop': B_B, 'rook': B_R, 'queen': B_Q}
    - 'material_values': {'white': white_val, 'black': black_val}
    - 'advantage': {'color': color, 'margin': margin}
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return {}
        
    prolog_board, _, _, _ = state_vars
    
    # 1. Query pieces lost
    white_lost = {}
    black_lost = {}
    
    try:
        q_white = f"pieces_lost({prolog_board}, white, P, N, B, R, Q)"
        res_w = list(prolog.query(q_white))
        if res_w:
            white_lost = {
                'pawn': int(res_w[0]['P']),
                'knight': int(res_w[0]['N']),
                'bishop': int(res_w[0]['B']),
                'rook': int(res_w[0]['R']),
                'queen': int(res_w[0]['Q'])
            }
            
        q_black = f"pieces_lost({prolog_board}, black, P, N, B, R, Q)"
        res_b = list(prolog.query(q_black))
        if res_b:
            black_lost = {
                'pawn': int(res_b[0]['P']),
                'knight': int(res_b[0]['N']),
                'bishop': int(res_b[0]['B']),
                'rook': int(res_b[0]['R']),
                'queen': int(res_b[0]['Q'])
            }
    except Exception as e:
        print(f"Error querying pieces lost: {e}")
        
    # 2. Query material value and advantage
    material_values = {}
    advantage = {}
    try:
        q_val_w = f"material_value({prolog_board}, white, Val)"
        res_val_w = list(prolog.query(q_val_w))
        w_val = int(res_val_w[0]['Val']) if res_val_w else 0
        
        q_val_b = f"material_value({prolog_board}, black, Val)"
        res_val_b = list(prolog.query(q_val_b))
        b_val = int(res_val_b[0]['Val']) if res_val_b else 0
        
        material_values = {'white': w_val, 'black': b_val}
        
        q_adv = f"material_advantage({prolog_board}, Color, Diff)"
        res_adv = list(prolog.query(q_adv))
        if res_adv:
            color = res_adv[0]['Color']
            if isinstance(color, bytes):
                color = color.decode('utf-8')
            margin = int(res_adv[0]['Diff'])
            
            # If the difference is 0, advantage is none
            if margin == 0:
                advantage = {'color': 'none', 'margin': 0}
            else:
                advantage = {'color': str(color), 'margin': margin}
        else:
            advantage = {'color': 'none', 'margin': 0}
    except Exception as e:
        print(f"Error querying material values/advantage: {e}")
        
    # 3. Query dynamic material value and advantage
    dynamic_material_values = {}
    dynamic_advantage = {}
    try:
        q_dyn_w = f"dynamic_material_value({prolog_board}, white, Val)"
        res_dyn_w = list(prolog.query(q_dyn_w))
        w_dyn = float(res_dyn_w[0]['Val']) if res_dyn_w else 0.0
        
        q_dyn_b = f"dynamic_material_value({prolog_board}, black, Val)"
        res_dyn_b = list(prolog.query(q_dyn_b))
        b_dyn = float(res_dyn_b[0]['Val']) if res_dyn_b else 0.0
        
        dynamic_material_values = {'white': round(w_dyn, 2), 'black': round(b_dyn, 2)}
        
        q_dyn_adv = f"dynamic_material_advantage({prolog_board}, Color, Diff)"
        res_dyn_adv = list(prolog.query(q_dyn_adv))
        if res_dyn_adv:
            color = res_dyn_adv[0]['Color']
            if isinstance(color, bytes):
                color = color.decode('utf-8')
            margin = float(res_dyn_adv[0]['Diff'])
            
            if abs(margin) < 0.01:
                dynamic_advantage = {'color': 'none', 'margin': 0.0}
            else:
                dynamic_advantage = {'color': str(color), 'margin': round(margin, 2)}
        else:
            dynamic_advantage = {'color': 'none', 'margin': 0.0}
    except Exception as e:
        print(f"Error querying dynamic material values/advantage: {e}")
        
    return {
        'white_lost': white_lost,
        'black_lost': black_lost,
        'material_values': material_values,
        'advantage': advantage,
        'dynamic_material_values': dynamic_material_values,
        'dynamic_advantage': dynamic_advantage
    }

def get_game_phase(fen: str) -> str:
    """
    Get the current game phase (opening, middlegame, or endgame) from the given FEN.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A string: "opening", "middlegame", or "endgame".
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return "middlegame"
        
    prolog_board, _, _, _ = state_vars
    query_string = f"game_phase({prolog_board}, Phase)"
    try:
        results = list(prolog.query(query_string))
        if results:
            phase = results[0]['Phase']
            if isinstance(phase, bytes):
                phase = phase.decode('utf-8')
            return str(phase)
    except Exception as e:
        print(f"Error querying game phase: {e}")
    return "middlegame"

def get_tension_points(fen: str) -> dict:
    """
    Identifies board tension points where opposing pawns or pieces can capture each other.
    """
    import chess
    try:
        board = chess.Board(fen)
    except Exception as e:
        print(f"Error parsing FEN in get_tension_points: {e}")
        return {"pawn_tension": [], "mutual_piece_tension": []}

    pawn_tensions = []
    piece_tensions = []
    
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
            
        color = piece.color
        opp_color = not color
        
        # Get attackers of opposite color
        attackers = board.attackers(opp_color, sq)
        for att_sq in attackers:
            # To avoid duplicates, only process pairs once (sq < att_sq)
            if sq >= att_sq:
                continue
                
            att_piece = board.piece_at(att_sq)
            if att_piece is None:
                continue
                
            # Check if it is a mutual attack
            is_mutual = sq in board.attackers(color, att_sq)
            
            sq_name = chess.square_name(sq)
            att_sq_name = chess.square_name(att_sq)
            
            # Classify
            if piece.piece_type == chess.PAWN and att_piece.piece_type == chess.PAWN:
                pawn_tensions.append(f"pawns at {sq_name} and {att_sq_name}")
            elif is_mutual:
                piece_type_name = chess.piece_name(piece.piece_type)
                att_piece_type_name = chess.piece_name(att_piece.piece_type)
                piece_tensions.append(f"{piece_type_name} at {sq_name} and {att_piece_type_name} at {att_sq_name}")
                
    return {
        "pawn_tension": sorted(pawn_tensions),
        "mutual_piece_tension": sorted(piece_tensions)
    }

def get_positional_evaluation(fen: str) -> dict:
    """
    Evaluates positional features including development completion, passed pawns, 
    backward pawns, weak squares, and the game phase from the given FEN.
    
    Parameters:
    - fen: The FEN string representing the board state.
    
    Returns:
    A dictionary containing:
    - 'game_phase': 'opening' | 'middlegame' | 'endgame'
    - 'development':
      - 'white_undeveloped': list of undeveloped pieces (e.g. ['knight at b1'])
      - 'white_complete': bool
      - 'black_undeveloped': list of undeveloped pieces
      - 'black_complete': bool
    - 'passed_pawns': list of passed pawns (e.g. [{'color': 'white', 'square': 'e4'}])
    - 'backward_pawns': list of backward pawns (e.g. [{'color': 'white', 'square': 'd3'}])
    - 'weak_squares': {'white': list of squares, 'black': list of squares}
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return {}
        
    prolog_board, _, _, _ = state_vars
    
    # 1. Game phase
    phase = get_game_phase(fen)
    
    # 2. Development status
    development = {
        'white_undeveloped': [],
        'white_complete': True,
        'black_undeveloped': [],
        'black_complete': True
    }
    
    try:
        q_w_pieces = f"starting_square(white, Type, X-Y), occupied({prolog_board}, X-Y, white, Type)"
        res_w = list(prolog.query(q_w_pieces))
        w_undev = []
        for r in res_w:
            t = r['Type']
            if isinstance(t, bytes): t = t.decode('utf-8')
            sq = f"{file_map_inv[r['X']]}{r['Y']}"
            w_undev.append(f"{t} at {sq}")
        development['white_undeveloped'] = sorted(w_undev)
        development['white_complete'] = (len(w_undev) == 0)
        
        q_b_pieces = f"starting_square(black, Type, X-Y), occupied({prolog_board}, X-Y, black, Type)"
        res_b = list(prolog.query(q_b_pieces))
        b_undev = []
        for r in res_b:
            t = r['Type']
            if isinstance(t, bytes): t = t.decode('utf-8')
            sq = f"{file_map_inv[r['X']]}{r['Y']}"
            b_undev.append(f"{t} at {sq}")
        development['black_undeveloped'] = sorted(b_undev)
        development['black_complete'] = (len(b_undev) == 0)
    except Exception as e:
        print(f"Error checking starting square occupancy: {e}")
        
    # 3. Passed pawns
    passed_pawns = []
    try:
        q_passed = f"is_passed_pawn({prolog_board}, Color, X-Y)"
        res_passed = list(prolog.query(q_passed))
        for r in res_passed:
            c = r['Color']
            if isinstance(c, bytes): c = c.decode('utf-8')
            sq = f"{file_map_inv[r['X']]}{r['Y']}"
            passed_pawns.append({'color': str(c), 'square': sq})
        seen = set()
        unique_passed = []
        for p in passed_pawns:
            k = (p['color'], p['square'])
            if k not in seen:
                seen.add(k)
                unique_passed.append(p)
        passed_pawns = sorted(unique_passed, key=lambda x: (x['color'], x['square']))
    except Exception as e:
        print(f"Error querying passed pawns: {e}")
        
    # 4. Backward pawns
    backward_pawns = []
    try:
        q_backward = f"is_backward_pawn({prolog_board}, Color, X-Y)"
        res_backward = list(prolog.query(q_backward))
        for r in res_backward:
            c = r['Color']
            if isinstance(c, bytes): c = c.decode('utf-8')
            sq = f"{file_map_inv[r['X']]}{r['Y']}"
            backward_pawns.append({'color': str(c), 'square': sq})
        seen = set()
        unique_backward = []
        for b in backward_pawns:
            k = (b['color'], b['square'])
            if k not in seen:
                seen.add(k)
                unique_backward.append(b)
        backward_pawns = sorted(unique_backward, key=lambda x: (x['color'], x['square']))
    except Exception as e:
        print(f"Error querying backward pawns: {e}")
        
    # 5. Weak squares
    weak_squares = {'white': [], 'black': []}
    try:
        q_weak_w = f"is_weak_square({prolog_board}, white, X-Y)"
        res_weak_w = list(prolog.query(q_weak_w))
        w_weak = []
        for r in res_weak_w:
            w_weak.append(f"{file_map_inv[r['X']]}{r['Y']}")
        weak_squares['white'] = sorted(list(set(w_weak)))
        
        q_weak_b = f"is_weak_square({prolog_board}, black, X-Y)"
        res_weak_b = list(prolog.query(q_weak_b))
        b_weak = []
        for r in res_weak_b:
            b_weak.append(f"{file_map_inv[r['X']]}{r['Y']}")
        weak_squares['black'] = sorted(list(set(b_weak)))
    except Exception as e:
        print(f"Error querying weak squares: {e}")
        
    # 6. Tension points
    board_tension = get_tension_points(fen)
        
    return {
        'game_phase': phase,
        'development': development,
        'passed_pawns': passed_pawns,
        'backward_pawns': backward_pawns,
        'weak_squares': weak_squares,
        'board_tension': board_tension
    }

def get_mate_in_one(fen: str) -> list[str]:
    """
    Find moves that immediately lead to checkmate.
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    query_string = f"mate_in_one(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), FromX-FromY, ToX-ToY)"
    try:
        results = list(prolog.query(query_string))
        moves = []
        for r in results:
            moves.append(f"{file_map_inv[r['FromX']]}{r['FromY']}{file_map_inv[r['ToX']]}{r['ToY']}")
        return sorted(list(set(moves)))
    except Exception as e:
        print(f"Error querying mate in one: {e}")
        return []

def get_mate_in_two(fen: str) -> list[str]:
    """
    Find moves that force a checkmate in 2 moves (3 plies total).
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    query_string = f"mate_in_two(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), FromX-FromY, ToX-ToY)"
    try:
        results = list(prolog.query(query_string))
        moves = []
        for r in results:
            moves.append(f"{file_map_inv[r['FromX']]}{r['FromY']}{file_map_inv[r['ToX']]}{r['ToY']}")
        return sorted(list(set(moves)))
    except Exception as e:
        print(f"Error querying mate in two: {e}")
        return []

def get_mate_in_three(fen: str) -> list[str]:
    """
    Find moves that force a checkmate in 3 moves (5 plies total).
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    query_string = f"mate_in_three(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), FromX-FromY, ToX-ToY)"
    try:
        results = list(prolog.query(query_string))
        moves = []
        for r in results:
            moves.append(f"{file_map_inv[r['FromX']]}{r['FromY']}{file_map_inv[r['ToX']]}{r['ToY']}")
        return sorted(list(set(moves)))
    except Exception as e:
        print(f"Error querying mate in three: {e}")
        return []

def get_forced_material_wins(fen: str) -> list[dict]:
    """
    Find moves that force a material win in 2 moves (3 plies total).
    Returns list of dicts: [{'move': 'd5c7', 'gain': 9}]
    """
    state_vars = parse_fen_to_prolog_vars(fen)
    if not state_vars:
        return []
    prolog_board, turn_color, prolog_rights, ep_file = state_vars
    query_string = f"forced_material_win_two(state({prolog_board}, {turn_color}, {prolog_rights}, {ep_file}), FromX-FromY, ToX-ToY, Promo, Gain)"
    try:
        results = list(prolog.query(query_string))
        wins = []
        for r in results:
            promo_val = r['Promo']
            suffix = ""
            if promo_val == 'knight':
                suffix = "n"
            elif promo_val == 'queen':
                suffix = "q"
            elif promo_val == 'rook':
                suffix = "r"
            elif promo_val == 'bishop':
                suffix = "b"
            
            wins.append({
                "move": f"{file_map_inv[r['FromX']]}{r['FromY']}{file_map_inv[r['ToX']]}{r['ToY']}{suffix}",
                "gain": int(r['Gain'])
            })
        # Deduplicate and sort by move, keeping the highest gain for each move
        move_to_gain = {}
        for w in wins:
            m = w['move']
            g = w['gain']
            if m not in move_to_gain or g > move_to_gain[m]:
                move_to_gain[m] = g
        sorted_wins = [{"move": m, "gain": g} for m, g in sorted(move_to_gain.items())]
        return sorted_wins
    except Exception as e:
        print(f"Error querying forced material wins: {e}")
        return []

def get_attackers_defenders(fen: str, square: str) -> dict:
    """
    Find all white and black pieces attacking a given square. 
    Helps evaluate trades, captures, and checkmate defense depth (e.g. 'take take take' chains).
    
    Parameters:
    - fen: The FEN string representing the current board state.
    - square: The coordinate of the square to check (e.g., 'd8', 'f7').
    
    Returns:
    A dictionary containing the piece on the square, list of white/black attackers, and counts.
    """
    import chess
    try:
        board = chess.Board(fen)
        sq_parsed = chess.parse_square(square.strip().lower())
        
        piece = board.piece_at(sq_parsed)
        piece_str = piece.symbol() if piece else "empty"
        
        # Get attackers
        white_attackers_indices = board.attackers(chess.WHITE, sq_parsed)
        black_attackers_indices = board.attackers(chess.BLACK, sq_parsed)
        
        def format_attackers(indices):
            res = []
            for idx in indices:
                p = board.piece_at(idx)
                res.append({
                    "piece": p.symbol() if p else "unknown",
                    "square": chess.square_name(idx)
                })
            return res
            
        w_att = format_attackers(white_attackers_indices)
        b_att = format_attackers(black_attackers_indices)
        
        # Friendly/Enemy context based on whose turn it is
        turn_color = "white" if board.turn == chess.WHITE else "black"
        friendly_attackers = w_att if turn_color == "white" else b_att
        enemy_attackers = b_att if turn_color == "white" else w_att
        
        # Simple safety evaluation recommendation
        safety_status = "stable"
        if len(friendly_attackers) > len(enemy_attackers):
            safety_status = f"friendly_has_majority ({len(friendly_attackers)} attackers vs {len(enemy_attackers)} defenders)"
        elif len(friendly_attackers) < len(enemy_attackers):
            safety_status = f"enemy_has_majority ({len(enemy_attackers)} attackers vs {len(friendly_attackers)} defenders)"
        else:
            safety_status = f"balanced ({len(friendly_attackers)} vs {len(enemy_attackers)})"
            
        return {
            "square": square,
            "piece_on_square": piece_str,
            "turn_color": turn_color,
            "white_attackers": w_att,
            "black_attackers": b_att,
            "white_attacker_count": len(w_att),
            "black_attacker_count": len(b_att),
            "friendly_attacker_count": len(friendly_attackers),
            "enemy_attacker_count": len(enemy_attackers),
            "exchange_safety": safety_status
        }
    except Exception as e:
        return {"error": f"Failed to get attackers/defenders: {e}"}


