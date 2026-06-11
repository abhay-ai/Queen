import os

def convert():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prolog_path = os.path.join(current_dir, "queen.pl")
    output_js_path = os.path.join(current_dir, "docs", "queen_engine.js")

    if not os.path.exists(prolog_path):
        print(f"Error: {prolog_path} not found.")
        return

    with open(prolog_path, "r", encoding="utf-8") as f:
        prolog_content = f.read()

    # 1. Replace between( with queen_between( and sum_list( with queen_sum_list( for Tau Prolog compatibility
    # Make sure we only match the predicate calls, not text in comments or variable names
    prolog_content = prolog_content.replace("between(", "queen_between(")
    prolog_content = prolog_content.replace("sum_list(", "queen_sum_list(")

    # 2. Replace SWI-Prolog specific format/3 calls with simple unifications for Tau Prolog
    prolog_content = prolog_content.replace(
        'format(string(Reason), "Illegal Move: The starting square ~w is completely empty. There is no piece there to move.", [From])',
        'Reason = "Illegal Move: The starting square is completely empty. There is no piece there to move."'
    )
    prolog_content = prolog_content.replace(
        'format(string(Reason), "Illegal Move: You attempted to move the opponent\'s ~w on ~w. You are playing as ~w.", [PieceType, From, Turn])',
        'Reason = "Illegal Move: You attempted to move the opponent\'s piece. It is not your turn."'
    )
    prolog_content = prolog_content.replace(
        'format(string(Reason), "CRITICAL FAILURE: Your King is currently in CHECK! The path ~w to ~w is illegal because it fails to protect or move your King out of danger.", [From, To])',
        'Reason = "CRITICAL FAILURE: Your King is currently in CHECK! This move fails to protect or move your King out of danger."'
    )
    prolog_content = prolog_content.replace(
        'format(string(Reason), "Illegal geometric trajectory: A ~w cannot physically move to ~w under standard chess rules, or the path is blocked by another piece.", [PieceType, To])',
        'Reason = "Illegal geometric trajectory: This piece cannot move to that square, or the path is blocked by another piece."'
    )

    # 3. Append custom implementations of queen_between/3, queen_sum_list/2, forall/2, and bridge utilities
    shims = """

% =====================================================================
% TAU PROLOG COMPATIBILITY SHIMS
% =====================================================================

queen_between(Low, High, Value) :-
    Value = Low.
queen_between(Low, High, Value) :-
    Low < High,
    Next is Low + 1,
    queen_between(Next, High, Value).

queen_sum_list([], 0).
queen_sum_list([H|T], Sum) :-
    queen_sum_list(T, Rest),
    Sum is H + Rest.

% forall/2 shim for Tau Prolog
forall(Cond, Action) :- \\+ (Cond, \\+ Action).

% delete/3 shim for Tau Prolog
delete([], _, []).
delete([X|T], X, Out) :- !, delete(T, X, Out).
delete([H|T], X, [H|Out]) :- delete(T, X, Out).

find_checking_pieces(Board, Color, Checking) :-
    (member(piece(Color, king, KingPos), Board) ->
        opponent(Color, Enemy),
        findall(piece(Enemy, EnemyType, EnemyPos), (
            member(piece(Enemy, EnemyType, EnemyPos), Board),
            move_piece(EnemyType, Board, none, EnemyPos, KingPos)
        ), Checking)
    ;
        Checking = []
    ).

js_tactical_summary(Board, Color, Rights, EP, GameStatus, InCheck, Checking, Pins, Threats, Defended, Discovered, Forks, WVal, BVal) :-
    % 1. Game status
    (game_status(state(Board, Color, Rights, EP), status(Status, Winner)) -> GameStatus = status(Status, Winner) ; GameStatus = status(active, none)),
    % 2. Check state
    (in_check(Board, Color) -> InCheck = true ; InCheck = false),
    % 3. Checking pieces
    find_checking_pieces(Board, Color, Checking),
    % 4. Pinned pieces
    find_pinned_pieces(Board, Color, Pins),
    % 5. Threatened pieces
    find_threats(Board, Color, Threats),
    % 6. Defended pieces
    find_defended_pieces(Board, Color, Defended),
    % 7. Discovered Attacks
    findall(da(Blocker, Attacker, Target), discovered_attack_candidate(Board, Color, Blocker, Attacker, Target), Discovered),
    % 8. Forks
    opponent(Color, Enemy),
    findall(fork(Forker, Target1, Target2, ForkStatus), (is_fork(Board, Enemy, Forker, Target1, Target2), fork_status(Board, Enemy, Forker, Target1, Target2, ForkStatus)), Forks),
    % 9. Material values
    (material_value(Board, white, WVal) -> true ; WVal = 0),
    (material_value(Board, black, BVal) -> true ; BVal = 0).
"""
    prolog_content += shims

    # 4. Escape backslashes and backticks for JS template literal safety
    escaped_prolog = prolog_content.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    # 5. Generate the Javascript wrapper using simple replace to avoid f-string escaping pain
    js_template = """// Queen Prolog Rulebase & JS Bridge for Browser Integration (Tau Prolog)
// Automatically generated from queen.pl via convert_prolog.py

const QUEEN_PROLOG_SOURCE = `
{{RULES}}
`;

// FEN parser in Javascript to convert a chess FEN to Prolog state terms
function parseFenToPrologVars(fen) {
    const fileMap = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8};
    const pieceMap = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'};
    
    try {
        const parts = fen.trim().split(/\\s+/);
        if (parts.length === 0 || !parts[0]) return null;
        
        const ranks = parts[0].split('/');
        const prologPieces = [];
        
        for (let rankIdx = 0; rankIdx < ranks.length; rankIdx++) {
            const rankStr = ranks[rankIdx];
            const prologRank = 8 - rankIdx;
            let fileIdx = 1;
            for (let i = 0; i < rankStr.length; i++) {
                const char = rankStr[i];
                if (/\\d/.test(char)) {
                    fileIdx += parseInt(char, 10);
                } else {
                    const color = char === char.toUpperCase() ? 'white' : 'black';
                    const type = pieceMap[char.toLowerCase()];
                    prologPieces.push(`piece(${color},${type},${fileIdx}-${prologRank})`);
                    fileIdx++;
                }
            }
        }
        
        const prologBoard = "[" + prologPieces.join(",") + "]";
        
        let turnColor = "white";
        if (parts.length > 1) {
            turnColor = parts[1] === "w" ? "white" : "black";
        }
        
        let prologRights = "[]";
        if (parts.length > 2) {
            const rightsStr = parts[2];
            const rights = [];
            if (rightsStr.includes('K')) rights.push('wk');
            if (rightsStr.includes('Q')) rights.push('wq');
            if (rightsStr.includes('k')) rights.push('bk');
            if (rightsStr.includes('q')) rights.push('bq');
            prologRights = "[" + rights.join(",") + "]";
        }
        
        let epFile = "none";
        if (parts.length > 3 && parts[3] !== '-') {
            const epSquare = parts[3];
            if (epSquare[0] in fileMap) {
                epFile = fileMap[epSquare[0]];
            }
        }
        
        return {
            prologBoard,
            turnColor,
            prologRights,
            epFile,
            term: `state(${prologBoard}, ${turnColor}, ${prologRights}, ${epFile})`
        };
    } catch (e) {
        console.error("Error parsing FEN in JS:", e);
        return null;
    }
}

// Initialize Tau Prolog Session
let plSession = null;
let plLoaded = false;

function initQueenEngine(onSuccess, onError) {
    if (plLoaded) {
        if (onSuccess) onSuccess();
        return;
    }
    
    try {
        // Create session
        plSession = pl.create(1000000);
        
        // Consult rules
        plSession.consult(QUEEN_PROLOG_SOURCE, {
            success: function() {
                plLoaded = true;
                console.log("Queen Prolog Engine initialized successfully.");
                if (onSuccess) onSuccess();
            },
            error: function(err) {
                console.error("Tau Prolog consult error:", err);
                if (onError) onError(err);
            }
        });
    } catch (e) {
        console.error("Failed to initialize Tau Prolog session:", e);
        if (onError) onError(e);
    }
}

// Helper function to query a single answer from Prolog
function queryPrologSingle(queryStr, callback) {
    if (!plLoaded) {
        callback(null, "Engine not initialized");
        return;
    }
    
    plSession.query(queryStr, {
        success: function() {
            plSession.answer(function(answer) {
                if (pl.type.is_substitution(answer)) {
                    callback(answer, null);
                } else if (pl.type.is_error(answer)) {
                    callback(null, answer);
                } else {
                    callback(null, "No answers found");
                }
            });
        },
        error: function(err) {
            callback(null, err);
        }
    });
}

// Helper function to query multiple answers from Prolog
function queryPrologAll(queryStr, callback) {
    if (!plLoaded) {
        callback([], "Engine not initialized");
        return;
    }
    
    plSession.query(queryStr, {
        success: function() {
            const results = [];
            function getNextAnswer() {
                plSession.answers(function(answer) {
                    if (pl.type.is_substitution(answer)) {
                        results.push(answer);
                        getNextAnswer();
                    } else {
                        callback(results, null);
                    }
                });
            }
            getNextAnswer();
        },
        error: function(err) {
            callback([], err);
        }
    });
}

// Convert Prolog term back to JS representation
function termToJs(term) {
    if (!term) return null;
    if (term.args && term.args.length > 0) {
        // Check for compound terms like X-Y
        if (term.indicator === "-/2") {
            return termToJs(term.args[0]) + "-" + termToJs(term.args[1]);
        }
        // Check for lists
        if (term.indicator === "./2") {
            const list = [];
            let current = term;
            while (current && current.indicator === "./2") {
                list.push(termToJs(current.args[0]));
                current = current.args[1];
            }
            return list;
        }
        // General compound term
        return {
            functor: term.id,
            args: term.args.map(termToJs)
        };
    }
    if (term.id === "[]") return [];
    return term.id !== undefined ? term.id : term.value;
}

// Public bridge API matching python methods
function jsCheckMoveDiagnostics(fen, moveUci, callback) {
    if (typeof moveUci !== "string" || moveUci.length < 4 || moveUci.length > 5) {
        callback(false, "Malformed string format. It must be 4 or 5 characters (e.g., e2e4 or e7e8q).");
        return;
    }
    const fileMap = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8};
    const fromSquare = moveUci.substring(0, 2);
    const toSquare = moveUci.substring(2, 4);
    
    if (!(fromSquare[0] in fileMap) || !/^[1-8]$/.test(fromSquare[1]) || !(toSquare[0] in fileMap) || !/^[1-8]$/.test(toSquare[1])) {
        callback(false, "Coordinates fall entirely outside the boundaries of an 8x8 chessboard grid.");
        return;
    }
    
    function getPieceAtSquare(fenStr, sq) {
        const fm = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7};
        const parts = fenStr.trim().split(/\\s+/);
        if (!parts || parts.length === 0) return null;
        const ranks = parts[0].split('/');
        const fIdx = fm[sq[0]];
        const rIdx = 8 - parseInt(sq[1], 10);
        if (rIdx < 0 || rIdx >= 8 || fIdx < 0 || fIdx >= 8) return null;
        const rStr = ranks[rIdx];
        let currentFile = 0;
        for (let i = 0; i < rStr.length; i++) {
            const char = rStr[i];
            if (/\\d/.test(char)) {
                currentFile += parseInt(char, 10);
            } else {
                if (currentFile === fIdx) return char;
                currentFile++;
            }
        }
        return null;
    }

    const pieceChar = getPieceAtSquare(fen, fromSquare);
    const isPawn = pieceChar && pieceChar.toLowerCase() === 'p';
    const toRank = parseInt(toSquare[1], 10);
    const isPromotionRank = (toRank === 8 || toRank === 1);
    const isPromoting = isPawn && isPromotionRank;

    if (isPromoting) {
        if (moveUci.length !== 5) {
            callback(false, "Pawn promotion moves must specify a promotion piece (e.g., e7e8q).");
            return;
        }
        const promoChar = moveUci[4].toLowerCase();
        if (promoChar !== 'q' && promoChar !== 'r' && promoChar !== 'b' && promoChar !== 'n') {
            callback(false, "Invalid promotion piece specified. Must be one of: q, r, b, n.");
            return;
        }
    } else {
        if (moveUci.length !== 4) {
            callback(false, "Non-promotion moves must be exactly 4 characters (e.g., e2e4).");
            return;
        }
    }
    
    const parsed = parseFenToPrologVars(fen);
    if (!parsed) {
        callback(false, "Invalid FEN board state.");
        return;
    }
    
    const plFrom = `${fileMap[fromSquare[0]]}-${fromSquare[1]}`;
    const plTo = `${fileMap[toSquare[0]]}-${toSquare[1]}`;
    
    const queryStr = `validate_and_explain(${parsed.term}, ${plFrom}, ${plTo}, Explanation).`;
    
    queryPrologSingle(queryStr, function(answer, err) {
        if (err) {
            callback(false, "Symbolic constraints exception: " + err);
            return;
        }
        const plExplanation = termToJs(answer.lookup("Explanation"));
        if (plExplanation === "SUCCESS") {
            callback(true, "");
        } else {
            let explanation = plExplanation || "Move rejected by core constraint engine.";
            explanation = explanation.replace(/\\b([1-8])-([1-8])\\b/g, (match, xStr, yStr) => {
                const x = parseInt(xStr, 10);
                const fileMapInv = {1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e', 6: 'f', 7: 'g', 8: 'h'};
                return (fileMapInv[x] || xStr) + yStr;
            });
            callback(false, explanation);
        }
    });
}

function jsGetLegalMoves(fen, callback) {
    const parsed = parseFenToPrologVars(fen);
    if (!parsed) {
        callback([]);
        return;
    }
    
    const queryStr = `legal_move(${parsed.term}, FromX-FromY, ToX-ToY, _).`;
    const fileMapInv = {1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e', 6: 'f', 7: 'g', 8: 'h'};
    
    queryPrologAll(queryStr, function(answers, err) {
        if (err) {
            callback([]);
            return;
        }
        const moves = new Set();
        answers.forEach(ans => {
            const fx = termToJs(ans.lookup("FromX"));
            const fy = termToJs(ans.lookup("FromY"));
            const tx = termToJs(ans.lookup("ToX"));
            const ty = termToJs(ans.lookup("ToY"));
            if (fx && fy && tx && ty) {
                const uci = `${fileMapInv[fx]}${fy}${fileMapInv[tx]}${ty}`;
                moves.add(uci);
                // Handle promotions
                const boardStr = parsed.prologBoard;
                const isWhitePawn = boardStr.includes(`piece(white,pawn,${fx}-${fy})`);
                const isBlackPawn = boardStr.includes(`piece(black,pawn,${fx}-${fy})`);
                if ((isWhitePawn && ty === 8) || (isBlackPawn && ty === 1)) {
                    moves.add(uci + 'q');
                    moves.add(uci + 'r');
                    moves.add(uci + 'b');
                    moves.add(uci + 'n');
                }
            }
        });
        callback(Array.from(moves).sort());
    });
}

function jsGetTacticalSummary(fen, callback) {
    const parsed = parseFenToPrologVars(fen);
    if (!parsed) {
        callback(null, "Invalid FEN");
        return;
    }
    
    const queryStr = `js_tactical_summary(${parsed.prologBoard}, ${parsed.turnColor}, ${parsed.prologRights}, ${parsed.epFile}, GameStatus, InCheck, Checking, Pins, Threats, Defended, Discovered, Forks, WVal, BVal).`;
    
    queryPrologSingle(queryStr, function(answer, err) {
        if (err) {
            callback(null, err);
            return;
        }
        if (!answer) {
            callback(null, "No answer from Prolog engine");
            return;
        }
        
        try {
            const gameStatusTerm = termToJs(answer.lookup("GameStatus"));
            const inCheck = termToJs(answer.lookup("InCheck")) === "true";
            const checkingRaw = termToJs(answer.lookup("Checking")) || [];
            const pinsRaw = termToJs(answer.lookup("Pins")) || [];
            const threatenedRaw = termToJs(answer.lookup("Threats")) || [];
            const defendedRaw = termToJs(answer.lookup("Defended")) || [];
            const discoveredRaw = termToJs(answer.lookup("Discovered")) || [];
            const forksRaw = termToJs(answer.lookup("Forks")) || [];
            const wVal = Number(termToJs(answer.lookup("WVal")) || 0);
            const bVal = Number(termToJs(answer.lookup("BVal")) || 0);
            
            const fileMapInv = {1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e', 6: 'f', 7: 'g', 8: 'h'};
            function squareToAlgebraic(posStr) {
                if (!posStr || !posStr.includes("-")) return posStr;
                const [x, y] = posStr.split("-").map(Number);
                return fileMapInv[x] + y;
            }
            
            const pinned_pieces = pinsRaw.map(p => ({
                piece: p.args[1],
                square: squareToAlgebraic(p.args[2])
            }));
            
            const checking_pieces = checkingRaw.map(p => ({
                piece: p.args[1],
                square: squareToAlgebraic(p.args[2])
            }));
            
            const threatened_pieces = threatenedRaw.map(p => ({
                piece: p.args[1],
                square: squareToAlgebraic(p.args[2])
            }));
            
            const defended_pieces = defendedRaw.map(p => ({
                piece: p.args[1],
                square: squareToAlgebraic(p.args[2])
            }));
            
            const discovered_attacks = discoveredRaw.map(da => ({
                blocker: squareToAlgebraic(da.args[0]),
                attacker: squareToAlgebraic(da.args[1]),
                target: squareToAlgebraic(da.args[2])
            }));
            
            const forks = {
                existing: forksRaw.map(f => ({
                    attacker: squareToAlgebraic(f.args[0]),
                    targets: [squareToAlgebraic(f.args[1]), squareToAlgebraic(f.args[2])],
                    status: f.args[3]
                })),
                moves_creating_forks: []
            };
            
            let statusName = "active";
            let winnerName = null;
            if (gameStatusTerm && gameStatusTerm.functor === "status") {
                statusName = gameStatusTerm.args[0];
                winnerName = gameStatusTerm.args[1] === "none" ? null : gameStatusTerm.args[1];
            }
            
            const margin = wVal - bVal;
            const advantage = {
                color: margin > 0 ? "white" : (margin < 0 ? "black" : "none"),
                margin: Math.abs(margin)
            };
            
            const summary = {
                in_check: inCheck,
                checking_pieces,
                game_status: { status: statusName, winner: winnerName },
                pinned_pieces,
                threatened_pieces,
                defended_pieces,
                discovered_attacks,
                forks,
                material_values: { white: wVal, black: bVal },
                advantage
            };
            
            callback(summary, null);
        } catch (e) {
            callback(null, "Error parsing bridge results: " + e);
        }
    });
}
""".replace("{{RULES}}", escaped_prolog)

    with open(output_js_path, "w", encoding="utf-8") as f:
        f.write(js_template)

    print(f"Successfully converted queen.pl and wrote JavaScript wrapper to {output_js_path}.")

if __name__ == "__main__":
    convert()
