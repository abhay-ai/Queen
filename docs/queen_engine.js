// Queen Prolog Rulebase & JS Bridge for Browser Integration (Tau Prolog)
// Automatically generated from queen.pl via convert_prolog.py

const QUEEN_PROLOG_SOURCE = `
:- use_module(library(lists)).

% =====================================================================
% 1. GEOMETRY & UTILITIES
% =====================================================================
on_board(X-Y) :- queen_between(1, 8, X), queen_between(1, 8, Y).

occupied(Board, X-Y, Color, Type) :- member(piece(Color, Type, X-Y), Board).
empty(Board, Position) :- \\+ member(piece(_, _, Position), Board).

opponent(white, black).
opponent(black, white).

% Directional Vectors
dir(rook, 1, 0).  dir(rook, -1, 0).  dir(rook, 0, 1).  dir(rook, 0, -1).
dir(bishop, 1, 1). dir(bishop, 1, -1). dir(bishop, -1, 1). dir(bishop, -1, -1).
dir(queen, DX, DY) :- dir(rook, DX, DY) ; dir(bishop, DX, DY).

aligned(rook, StartX-StartY, EndX-EndY, DX, DY) :-
    (StartX =:= EndX -> DX = 0, (EndY > StartY -> DY = 1 ; DY = -1) ;
     StartY =:= EndY -> DY = 0, (EndX > StartX -> DX = 1 ; DX = -1)).

aligned(bishop, StartX-StartY, EndX-EndY, DX, DY) :-
    XDiff is EndX - StartX, YDiff is EndY - StartY,
    abs(XDiff) =:= abs(YDiff),
    (XDiff > 0 -> DX = 1 ; DX = -1),
    (YDiff > 0 -> DY = 1 ; DY = -1).

aligned(queen, Start, End, DX, DY) :-
    aligned(rook, Start, End, DX, DY) ; aligned(bishop, Start, End, DX, DY).

% Generator for candidate target squares (very fast alternative to on_board/1 loop)
candidate_target(pawn, _, X-Y, TX-TY) :-
    (TX = X, (TY is Y + 1 ; TY is Y + 2 ; TY is Y - 1 ; TY is Y - 2)) ;
    ((TX is X + 1 ; TX is X - 1), (TY is Y + 1 ; TY is Y - 1)).

candidate_target(knight, _, X-Y, TX-TY) :-
    member(DX-DY, [1-2, 1-(-2), -1-2, -1-(-2), 2-1, 2-(-2), -2-1, -2-(-2)]),
    TX is X + DX, TY is Y + DY.

candidate_target(king, _, X-Y, TX-TY) :-
    member(DX-DY, [1-0, -1-0, 0-1, 0-(-1), 1-1, 1-(-1), -1-1, -1-(-1)]),
    TX is X + DX, TY is Y + DY.

candidate_target(Type, Board, Start, End) :-
    member(Type, [rook, bishop, queen]),
    dir(Type, DX, DY),
    valid_path_squares(Board, Start, DX, DY, End).

valid_path_squares(Board, StartX-StartY, DX, DY, EndX-EndY) :-
    NextX is StartX + DX, NextY is StartY + DY,
    on_board(NextX-NextY),
    (
        EndX = NextX, EndY = NextY
        ;
        empty(Board, NextX-NextY),
        valid_path_squares(Board, NextX-NextY, DX, DY, EndX-EndY)
    ).

% =====================================================================
% 2. CORE PIECE LOGIC (move_piece/5)
% =====================================================================

% Normal Pawn Moves
move_piece(pawn, Board, _, X-Y1, X-Y2) :-
    occupied(Board, X-Y1, white, pawn), Y2 is Y1 + 1, empty(Board, X-Y2).
move_piece(pawn, Board, _, X-2, X-4) :-
    occupied(Board, X-2, white, pawn), empty(Board, X-3), empty(Board, X-4).
move_piece(pawn, Board, _, X-Y1, X-Y2) :-
    occupied(Board, X-Y1, black, pawn), Y2 is Y1 - 1, empty(Board, X-Y2).
move_piece(pawn, Board, _, X-7, X-5) :-
    occupied(Board, X-7, black, pawn), empty(Board, X-6), empty(Board, X-5).

% Normal Pawn Captures
move_piece(pawn, Board, _, X1-Y1, X2-Y2) :-
    occupied(Board, X1-Y1, Color, pawn), opponent(Color, Enemy),
    (Color == white -> Y2 is Y1 + 1 ; Y2 is Y1 - 1),
    (X2 is X1 + 1 ; X2 is X1 - 1), occupied(Board, X2-Y2, Enemy, _).

% En Passant Captures
move_piece(pawn, Board, EP_File, X1-5, X2-6) :-
    occupied(Board, X1-5, white, pawn), EP_File \\== none, X2 is EP_File,
    (X2 is X1 + 1 ; X2 is X1 - 1).
move_piece(pawn, Board, EP_File, X1-4, X2-3) :-
    occupied(Board, X1-4, black, pawn), EP_File \\== none, X2 is EP_File,
    (X2 is X1 + 1 ; X2 is X1 - 1).

% Knights & Kings
move_piece(knight, Board, _, StartX-StartY, EndX-EndY) :-
    occupied(Board, StartX-StartY, Color, knight),
    XDiff is abs(StartX - EndX), YDiff is abs(StartY - EndY),
    ((XDiff =:= 1, YDiff =:= 2) ; (XDiff =:= 2, YDiff =:= 1)),
    \\+ occupied(Board, EndX-EndY, Color, _).

move_piece(king, Board, _, StartX-StartY, EndX-EndY) :-
    occupied(Board, StartX-StartY, Color, king),
    XDiff is abs(StartX - EndX), YDiff is abs(StartY - EndY),
    XDiff =< 1, YDiff =< 1, (StartX =\\= EndX ; StartY =\\= EndY),
    \\+ occupied(Board, EndX-EndY, Color, _).

% Sliding Pieces
move_piece(Type, Board, _, Start, End) :-
    member(Type, [rook, bishop, queen]), occupied(Board, Start, Color, Type),
    (ground(End) ->
        aligned(Type, Start, End, DX, DY)
    ;
        dir(Type, DX, DY)
    ),
    valid_path(Board, Start, End, DX, DY, Color).

valid_path(Board, StartX-StartY, EndX-EndY, DX, DY, OurColor) :-
    NextX is StartX + DX, NextY is StartY + DY, on_board(NextX-NextY),
    (NextX =:= EndX, NextY =:= EndY -> \\+ occupied(Board, NextX-NextY, OurColor, _)
    ; empty(Board, NextX-NextY), valid_path(Board, NextX-NextY, EndX-EndY, DX, DY, OurColor)).

% =====================================================================
% 3. CASTLING & TRANSITIONS
% =====================================================================

% King-side Castling
execute_castle(Board, white, king, [piece(white,king,7-1), piece(white,rook,6-1) | Clean]) :-
    select(piece(white,king,5-1), Board, B1), select(piece(white,rook,8-1), B1, Clean),
    empty(Board, 6-1), empty(Board, 7-1), \\+ in_check(Board, white).
execute_castle(Board, black, king, [piece(black,king,7-8), piece(black,rook,6-8) | Clean]) :-
    select(piece(black,king,5-8), Board, B1), select(piece(black,rook,8-8), B1, Clean),
    empty(Board, 6-8), empty(Board, 7-8), \\+ in_check(Board, black).

% Queen-side Castling
execute_castle(Board, white, queen, [piece(white,king,3-1), piece(white,rook,4-1) | Clean]) :-
    select(piece(white,king,5-1), Board, B1), select(piece(white,rook,1-1), B1, Clean),
    empty(Board, 2-1), empty(Board, 3-1), empty(Board, 4-1), \\+ in_check(Board, white).
execute_castle(Board, black, queen, [piece(black,king,3-8), piece(black,rook,4-8) | Clean]) :-
    select(piece(black,king,5-8), Board, B1), select(piece(black,rook,1-8), B1, Clean),
    empty(Board, 2-8), empty(Board, 3-8), empty(Board, 4-8), \\+ in_check(Board, black).

% Standard Move Execution (including side effects like En Passant clears)
execute_standard_move(Board, EP_File, FromX-FromY, ToX-ToY, NewBoard) :-
    select(piece(Color, Type, FromX-FromY), Board, TempBoard1),
    % If En Passant capture occurred, delete the victim pawn behind the target square
    (Type == pawn, FromX \\== ToX, ToX == EP_File, empty(Board, ToX-ToY) ->
        select(piece(_, pawn, ToX-FromY), TempBoard1, TempBoard2)
    ;   
        (select(piece(_, _, ToX-ToY), TempBoard1, TempBoard2) -> true ; TempBoard2 = TempBoard1)
    ),
    % Pawn Promotion Backtracking (to Queen, Rook, Bishop, or Knight)
    (Type == pawn, (ToY =:= 8 ; ToY =:= 1) ->
        member(PromotedType, [queen, rook, bishop, knight]),
        NewBoard = [piece(Color, PromotedType, ToX-ToY) | TempBoard2]
    ;
        NewBoard = [piece(Color, Type, ToX-ToY) | TempBoard2]
    ).


% =====================================================================
% 4. COMPREHENSIVE REFEREE ENGINE (legal_move/4)
% =====================================================================

in_check(Board, Color) :-
    member(piece(Color, king, KingPos), Board), opponent(Color, Enemy),
    member(piece(Enemy, EnemyType, EnemyPos), Board),
    move_piece(EnemyType, Board, none, EnemyPos, KingPos).

is_in_check(state(Board, Color, _, _)) :- in_check(Board, Color).

% Entry Point 1: Standard Movement Validation
legal_move(state(Board, Color, Rights, EP), From, To, state(NewBoard, NextColor, NewRights, NewEP)) :-
    occupied(Board, From, Color, Type),
    (ground(To) -> true ; candidate_target(Type, Board, From, To)),
    on_board(To),
    move_piece(Type, Board, EP, From, To),
    execute_standard_move(Board, EP, From, To, NewBoard),
    \\+ in_check(NewBoard, Color),
    opponent(Color, NextColor),
    
    % Unpack coordinates safely up-front using pattern matching
    From = FromX-FromY,
    To = _ToX-ToY,
    
    % Calculate dynamic en passant metadata updates using the raw integers
    (Type == pawn, abs(FromY - ToY) =:= 2 -> 
        NewEP = FromX 
    ; 
        NewEP = none
    ),
    update_castling_rights(Rights, Type, From, NewRights).

% Entry Point 2: Castling Validation
legal_move(state(Board, Color, Rights, _), From, To, state(NewBoard, NextColor, NewRights, none)) :-
    is_castle_coordinates(Color, From, To, Side),
    can_castle_right(Rights, Color, Side),
    execute_castle(Board, Color, Side, NewBoard),
    % In-between square check protection
    castle_transit_square(Color, Side, MidSquare), \\+ (execute_standard_move(Board, none, From, MidSquare, MidBoard), in_check(MidBoard, Color)),
    opponent(Color, NextColor),
    update_castling_rights(Rights, king, From, NewRights).

% Helpers for state tracking
element_y(_-Y) :- Y.
is_castle_coordinates(white, 5-1, 7-1, king).  is_castle_coordinates(white, 5-1, 3-1, queen).
is_castle_coordinates(black, 5-8, 7-8, king).  is_castle_coordinates(black, 5-8, 3-8, queen).
can_castle_right(Rights, white, king) :- member(wk, Rights). can_castle_right(Rights, white, queen) :- member(wq, Rights).
can_castle_right(Rights, black, king) :- member(bk, Rights). can_castle_right(Rights, black, queen) :- member(bq, Rights).

update_castling_rights(Old, king, 5-1, New) :- delete(Old, wk, T), delete(T, wq, New).
update_castling_rights(Old, king, 5-8, New) :- delete(Old, bk, T), delete(T, bq, New).
update_castling_rights(Old, rook, 1-1, New) :- delete(Old, wq, New).
update_castling_rights(Old, rook, 8-1, New) :- delete(Old, wk, New).
update_castling_rights(Old, rook, 1-8, New) :- delete(Old, bq, New).
update_castling_rights(Old, rook, 8-8, New) :- delete(Old, bk, New).
update_castling_rights(Old, _, _, Old).

castle_transit_square(white, king, 6-1). castle_transit_square(white, queen, 4-1).
castle_transit_square(black, king, 6-8). castle_transit_square(black, queen, 4-8).

% =====================================================================
% 5. STALEMATE & ENDGAME EVALUATION
% =====================================================================
has_any_legal_move(Board, Color, Rights, EP) :-
    legal_move(state(Board, Color, Rights, EP), _From, _To, _NextState), !.

game_status(state(Board, Color, Rights, EP), status(checkmate, Enemy)) :-
    in_check(Board, Color), \\+ has_any_legal_move(Board, Color, Rights, EP), opponent(Color, Enemy).
game_status(state(Board, Color, Rights, EP), status(stalemate, none)) :-
    \\+ in_check(Board, Color), \\+ has_any_legal_move(Board, Color, Rights, EP).
game_status(_, status(active, none)).


% Wrapper to validate the move or catch the exact failure reason
validate_and_explain(State, From, To, "SUCCESS") :-
    legal_move(State, From, To, _), !.

% Failure Case 1: Moving from an empty square
validate_and_explain(state(Board, _, _, _), From, _, Reason) :-
    \\+ member(piece(_, _, From), Board), !,
    Reason = "Illegal Move: The starting square is completely empty. There is no piece there to move.".

% Failure Case 2: Moving the opponent's piece
validate_and_explain(state(Board, Turn, _, _), From, _, Reason) :-
    member(piece(Owner, PieceType, From), Board),
    Owner \\= Turn, !,
    Reason = "Illegal Move: You attempted to move the opponent's piece. It is not your turn.".

% Failure Case 3: The King is in check and this move fails to resolve it
validate_and_explain(State, From, To, Reason) :-
    is_in_check(State), % Assumes your file has an existing check-detection predicate
    \\+ legal_move(State, From, To, _), !,
    Reason = "CRITICAL FAILURE: Your King is currently in CHECK! This move fails to protect or move your King out of danger.".

% Failure Case 4: Standard geometric/structural rule violation
validate_and_explain(state(Board, _, _, _), From, To, Reason) :-
    member(piece(_, PieceType, From), Board), !,
    Reason = "Illegal geometric trajectory: This piece cannot move to that square, or the path is blocked by another piece.".


% =====================================================================
% 6. TACTICAL ANALYTICS
% =====================================================================

% A square X-Y is attacked by Enemy if Enemy can move a piece to it.
is_attacked(Board, Color, X-Y) :-
    opponent(Color, Enemy),
    member(piece(Enemy, EnemyType, EnemyPos), Board),
    move_piece(EnemyType, Board, none, EnemyPos, X-Y).

% A square X-Y is defended by friendly pieces of Color.
% We simulate placing an opponent piece there to see if our pieces can capture it.
is_defended(Board, Color, X-Y) :-
    member(piece(Color, PieceType, PiecePos), Board),
    PiecePos \\== X-Y,
    opponent(Color, Enemy),
    (select(piece(Color, _, X-Y), Board, CleanBoard) -> true ; CleanBoard = Board),
    TempBoard = [piece(Enemy, pawn, X-Y) | CleanBoard],
    move_piece(PieceType, TempBoard, none, PiecePos, X-Y).

% A piece at PiecePos of Color is pinned if removing it puts Color's King in check.
is_pinned(Board, Color, PiecePos) :-
    member(piece(Color, Type, PiecePos), Board),
    Type \\== king,
    \\+ in_check(Board, Color),  % The King must NOT be in check currently
    select(piece(Color, Type, PiecePos), Board, TempBoard),
    in_check(TempBoard, Color).


% Find all pinned pieces of Color: returns a list of piece(Color, Type, Pos)
find_pinned_pieces(Board, Color, Pinned) :-
    findall(piece(Color, Type, Pos), (member(piece(Color, Type, Pos), Board), is_pinned(Board, Color, Pos)), Pinned).

% Find all threatened friendly pieces: pieces of Color under attack by opponent
find_threats(Board, Color, Threatened) :-
    findall(piece(Color, Type, Pos), (member(piece(Color, Type, Pos), Board), is_attacked(Board, Color, Pos)), Threatened).

% Find all defended friendly pieces: pieces of Color that are protected by friendly pieces
find_defended_pieces(Board, Color, Defended) :-
    findall(piece(Color, Type, Pos), (member(piece(Color, Type, Pos), Board), is_defended(Board, Color, Pos)), Defended).

% Discovered Attack setup:
% Blocker is a friendly piece of Color.
% Attacker is a friendly slider (rook, bishop, queen) of Color.
% Target is an enemy piece.
% If Blocker is removed, Attacker has a clear line to attack Target, which was previously blocked.
discovered_attack_candidate(Board, Color, BlockerPos, AttackerPos, TargetPos) :-
    member(piece(Color, AttackerType, AttackerPos), Board),
    member(AttackerType, [rook, bishop, queen]),
    opponent(Color, Enemy),
    member(piece(Enemy, _TargetType, TargetPos), Board),
    aligned(AttackerType, AttackerPos, TargetPos, DX, DY),
    \\+ move_piece(AttackerType, Board, none, AttackerPos, TargetPos),
    member(piece(Color, BlockerType, BlockerPos), Board),
    BlockerPos \\== AttackerPos, BlockerPos \\== TargetPos,
    aligned(AttackerType, AttackerPos, BlockerPos, DX, DY),
    aligned(AttackerType, BlockerPos, TargetPos, DX, DY),
    select(piece(Color, BlockerType, BlockerPos), Board, CleanBoard),
    move_piece(AttackerType, CleanBoard, none, AttackerPos, TargetPos).

% A piece at ForkerPos of Color forks EnemyPos1 and EnemyPos2.
is_fork(Board, Color, ForkerPos, EnemyPos1, EnemyPos2) :-
    member(piece(Color, ForkerType, ForkerPos), Board),
    opponent(Color, Enemy),
    member(piece(Enemy, _Type1, EnemyPos1), Board),
    move_piece(ForkerType, Board, none, ForkerPos, EnemyPos1),
    member(piece(Enemy, _Type2, EnemyPos2), Board),
    EnemyPos1 @< EnemyPos2,
    move_piece(ForkerType, Board, none, ForkerPos, EnemyPos2).

% Classify the safety and tactical value of a fork
fork_status(Board, Color, ForkerPos, EnemyPos1, EnemyPos2, Status) :-
    % 1. Attacker safety check
    (is_attacked(Board, Color, ForkerPos) ->
        (is_defended(Board, Color, ForkerPos) ->
            AttackerStatus = defended
        ;
            AttackerStatus = hanging
        )
    ;
        AttackerStatus = safe
    ),
    
    % 2. Targets defense check
    opponent(Color, Enemy),
    (is_defended(Board, Enemy, EnemyPos1) -> T1Def = defended ; T1Def = undefended),
    (is_defended(Board, Enemy, EnemyPos2) -> T2Def = defended ; T2Def = undefended),
    
    % 3. Check values of targets and attacker to determine tactical value
    member(piece(Color, ForkerType, ForkerPos), Board),
    member(piece(Enemy, T1Type, EnemyPos1), Board),
    member(piece(Enemy, T2Type, EnemyPos2), Board),
    piece_value(ForkerType, ForkerVal),
    piece_value(T1Type, T1Val),
    piece_value(T2Type, T2Val),
    
    % Determine status
    (AttackerStatus == hanging ->
        (T1Val > ForkerVal ; T2Val > ForkerVal ->
            Status = winning_sacrifice
        ;
            Status = unsafe_attacker_hangs
        )
    ;
        (T1Def == undefended ->
            Status = winning_fork
        ;
            (T2Def == undefended ->
                Status = winning_fork
            ;
                (T1Val > ForkerVal ; T2Val > ForkerVal ->
                    Status = winning_trade
                ;
                    Status = defended_trade
                )
            )
        )
    ).

% A move From -> To creates a fork on EnemyPos1 and EnemyPos2.
creates_fork(state(Board, Color, Rights, EP), From, To, EnemyPos1, EnemyPos2) :-
    legal_move(state(Board, Color, Rights, EP), From, To, state(NewBoard, _, _, _)),
    is_fork(NewBoard, Color, To, EnemyPos1, EnemyPos2).

% =====================================================================
% 7. ADVANCED STRATEGIC EVALUATIONS
% =====================================================================

% --- Development Status ---
starting_square(white, knight, 2-1).
starting_square(white, knight, 7-1).
starting_square(white, bishop, 3-1).
starting_square(white, bishop, 6-1).
starting_square(black, knight, 2-8).
starting_square(black, knight, 7-8).
starting_square(black, bishop, 3-8).
starting_square(black, bishop, 6-8).

undeveloped_pieces(Board, Color, Pieces) :-
    findall(piece(Color, Type, Pos), (
        starting_square(Color, Type, Pos),
        occupied(Board, Pos, Color, Type)
    ), Pieces).

is_development_complete(Board, Color) :-
    undeveloped_pieces(Board, Color, []).

% --- Pieces Lost & Material Value ---
count_piece(Board, Color, Type, Count) :-
    findall(Pos, member(piece(Color, Type, Pos), Board), List),
    length(List, Count).

lost_count(Board, Color, Type, Initial, Lost) :-
    count_piece(Board, Color, Type, Current),
    Diff is Initial - Current,
    (Diff > 0 -> Lost = Diff ; Lost = 0).

pieces_lost(Board, Color, Pawns, Knights, Bishops, Rooks, Queens) :-
    lost_count(Board, Color, pawn, 8, Pawns),
    lost_count(Board, Color, knight, 2, Knights),
    lost_count(Board, Color, bishop, 2, Bishops),
    lost_count(Board, Color, rook, 2, Rooks),
    lost_count(Board, Color, queen, 1, Queens).

piece_value(pawn, 1).
piece_value(knight, 3).
piece_value(bishop, 3).
piece_value(rook, 5).
piece_value(queen, 9).
piece_value(king, 0).

material_value(Board, Color, Value) :-
    findall(Val, (member(piece(Color, Type, _), Board), piece_value(Type, Val)), Vals),
    queen_sum_list(Vals, Value).

material_advantage(Board, AdvantageColor, Difference) :-
    material_value(Board, white, WhiteVal),
    material_value(Board, black, BlackVal),
    (WhiteVal >= BlackVal ->
        AdvantageColor = white,
        Difference is WhiteVal - BlackVal
    ;
        AdvantageColor = black,
        Difference is BlackVal - WhiteVal
    ).

% --- Pawn Structure & Weak Squares ---
in_front(white, Rank, OppRank) :- OppRank > Rank.
in_front(black, Rank, OppRank) :- OppRank < Rank.

adjacent_or_same_file(File, EnemyFile) :-
    queen_between(1, 8, EnemyFile),
    abs(File - EnemyFile) =< 1.

is_passed_pawn(Board, Color, File-Rank) :-
    occupied(Board, File-Rank, Color, pawn),
    opponent(Color, Enemy),
    \\+ (
        occupied(Board, EnemyFile-EnemyRank, Enemy, pawn),
        adjacent_or_same_file(File, EnemyFile),
        in_front(Color, Rank, EnemyRank)
    ).

is_pawn_attacked(Board, Color, File-Rank) :-
    opponent(Color, Enemy),
    (Color == white -> EnemyRank is Rank + 1 ; EnemyRank is Rank - 1),
    (EnemyFile is File - 1 ; EnemyFile is File + 1),
    on_board(EnemyFile-EnemyRank),
    occupied(Board, EnemyFile-EnemyRank, Enemy, pawn).

adjacent_pawns_advanced(Board, Color, File-Rank) :-
    (
        (AdjFile is File - 1 ; AdjFile is File + 1),
        on_board(AdjFile-AdjRank),
        occupied(Board, AdjFile-AdjRank, Color, pawn)
    ),
    \\+ (
        (AdjFile2 is File - 1 ; AdjFile2 is File + 1),
        on_board(AdjFile2-AdjRank2),
        occupied(Board, AdjFile2-AdjRank2, Color, pawn),
        (Color == white -> AdjRank2 =< Rank ; AdjRank2 >= Rank)
    ).

is_backward_pawn(Board, Color, File-Rank) :-
    occupied(Board, File-Rank, Color, pawn),
    adjacent_pawns_advanced(Board, Color, File-Rank),
    (Color == white -> NextRank is Rank + 1 ; NextRank is Rank - 1),
    on_board(File-NextRank),
    is_pawn_attacked(Board, Color, File-NextRank).

is_weak_square(Board, Color, File-Rank) :-
    queen_between(1, 8, File),
    (Color == white -> queen_between(3, 4, Rank) ; queen_between(5, 6, Rank)),
    \\+ occupied(Board, File-Rank, Color, pawn),
    \\+ (
        (AdjFile is File - 1 ; AdjFile is File + 1),
        on_board(AdjFile-AdjRank),
        occupied(Board, AdjFile-AdjRank, Color, pawn),
        (Color == white -> AdjRank < Rank ; AdjRank > Rank)
    ).

% --- Game Phase Detection ---
total_non_king_material(Board, TotalValue) :-
    findall(Val, (
        member(piece(_, Type, _), Board),
        Type \\== king,
        piece_value(Type, Val)
    ), Vals),
    queen_sum_list(Vals, TotalValue).

game_phase(Board, opening) :-
    (
        undeveloped_pieces(Board, white, WUndev), length(WUndev, WLen), WLen > 1
        ;
        undeveloped_pieces(Board, black, BUndev), length(BUndev, BLen), BLen > 1
    ),
    total_non_king_material(Board, TotalMaterial),
    TotalMaterial > 30, !.
game_phase(Board, endgame) :-
    total_non_king_material(Board, TotalMaterial),
    TotalMaterial =< 26, !.
game_phase(_, middlegame).

% =====================================================================
% 8. MULTI-STEP TACTICAL SEARCH
% =====================================================================

% Calculate net material difference: OurValue - EnemyValue
net_material_difference(Board, Color, Diff) :-
    material_value(Board, Color, OurVal),
    opponent(Color, Enemy),
    material_value(Board, Enemy, EnemyVal),
    Diff is OurVal - EnemyVal.

% Mate-in-1: A move immediately leads to checkmate
mate_in_one(State, FromX-FromY, ToX-ToY) :-
    legal_move(State, FromX-FromY, ToX-ToY, NextState),
    game_status(NextState, status(checkmate, _)).

% Mate-in-2: For all opponent replies, we have a follow-up mate-in-1
mate_in_two(State, FromX-FromY, ToX-ToY) :-
    legal_move(State, FromX-FromY, ToX-ToY, NextState),
    game_status(NextState, status(active, none)),
    forall(
        legal_move(NextState, _OppFrom, _OppTo, OppNextState),
        (
            legal_move(OppNextState, _, _, FinalState),
            game_status(FinalState, status(checkmate, _))
        )
    ).

% Mate-in-3: For all opponent replies, we have a follow-up mate-in-2 (5 plies total)
mate_in_three(State, FromX-FromY, ToX-ToY) :-
    legal_move(State, FromX-FromY, ToX-ToY, NextState),
    game_status(NextState, status(active, none)),
    forall(
        legal_move(NextState, _OppFrom, _OppTo, OppNextState),
        (
            once(mate_in_two(OppNextState, _, _))
        )
    ).

% Forced material win in 2 moves (3 plies total: white -> black -> white)
% Returns MinGain as the maximum guaranteed material gain (9=Queen, 5=Rook, 3=Minor, 1=Pawn)
forced_material_win_two(State, FromX-FromY, ToX-ToY, Promo, MinGain) :-
    State = state(Board, Color, _, _),
    net_material_difference(Board, Color, InitialDiff),
    member(MinGain, [9, 5, 3, 1]),
    legal_move(State, FromX-FromY, ToX-ToY, state(NextBoard, Enemy, NextRights, NextEP)),
    (occupied(Board, FromX-FromY, Color, pawn), (ToY =:= 8 ; ToY =:= 1) ->
        occupied(NextBoard, ToX-ToY, Color, Promo)
    ;
        Promo = none
    ),
    \\+ game_status(state(NextBoard, Enemy, NextRights, NextEP), status(checkmate, Color)),
    \\+ game_status(state(NextBoard, Enemy, NextRights, NextEP), status(stalemate, none)),
    forall(
        legal_move(state(NextBoard, Enemy, NextRights, NextEP), _OppFrom, _OppTo, state(OppNextBoard, Color, OppNextRights, OppNextEP)),
        (
            game_status(state(OppNextBoard, Color, OppNextRights, OppNextEP), status(checkmate, Enemy))
            ;
            (
                legal_move(state(OppNextBoard, Color, OppNextRights, OppNextEP), _FromX3-_FromY3, ToX3-ToY3, state(FinalBoard, Enemy, _, _)),
                (
                    is_attacked(FinalBoard, Color, ToX3-ToY3) ->
                        member(piece(Color, CapPieceType, ToX3-ToY3), FinalBoard),
                        piece_value(CapPieceType, CapValue),
                        net_material_difference(FinalBoard, Color, TempDiff),
                        FinalDiff is TempDiff - CapValue
                    ;
                        net_material_difference(FinalBoard, Color, FinalDiff)
                ),
                RequiredDiff is InitialDiff + MinGain,
                FinalDiff >= RequiredDiff
            )
        )
    ).


% =====================================================================
% 9. DYNAMIC PIECE VALUATION & MOBILITY
% =====================================================================

% Calculate mobility of a piece (number of legal target squares it can reach)
piece_mobility(Board, Type, StartX-StartY, Mobility) :-
    findall(EndX-EndY, (on_board(EndX-EndY), move_piece(Type, Board, none, StartX-StartY, EndX-EndY)), Ends),
    length(Ends, Mobility).

% Base values for dynamic piece evaluation (pawn=100, king=0)
base_piece_value(pawn, 100).
base_piece_value(knight, 300).
base_piece_value(bishop, 305).
base_piece_value(rook, 500).
base_piece_value(queen, 900).
base_piece_value(king, 0).

% Compute dynamic value of a piece based on its location and mobility
dynamic_piece_value(Board, Color, pawn, X-Y, Value) :-
    base_piece_value(pawn, Base),
    (is_passed_pawn(Board, Color, X-Y) ->
        (Color == white -> RankProgress is Y - 2 ; RankProgress is 7 - Y),
        Bonus is RankProgress * 15,
        Value is Base + Bonus
    ;
        Value is Base
    ), !.

dynamic_piece_value(_Board, Color, knight, X-Y, Value) :-
    base_piece_value(knight, Base),
    % Centralization bonus on 5th/6th rank (white) or 3rd/4th rank (black)
    (
        X >= 3, X =< 6,
        (Color == white -> (Y == 5 ; Y == 6) ; (Y == 3 ; Y == 4)) ->
        Value1 is Base + 100
    ;
        Value1 is Base
    ),
    % Edge penalty
    (
        (X == 1 ; X == 8) ->
        Value is Value1 - 25
    ;
        Value is Value1
    ), !.

dynamic_piece_value(Board, _Color, bishop, X-Y, Value) :-
    base_piece_value(bishop, Base),
    piece_mobility(Board, bishop, X-Y, Mobility),
    % Bishop mobility bonus: +8 points per square.
    % If trapped/blocked (mobility <= 2), apply a -100 points penalty
    (Mobility =< 2 ->
        Value is Base + Mobility * 8 - 100
    ;
        Value is Base + Mobility * 8
    ), !.

dynamic_piece_value(_Board, _Color, Type, _X-_Y, Value) :-
    base_piece_value(Type, Base),
    Value is Base.

% Sum up dynamic values of all pieces for Color
dynamic_material_value(Board, Color, Value) :-
    findall(Val, (member(piece(Color, Type, X-Y), Board), dynamic_piece_value(Board, Color, Type, X-Y, Val)), Vals),
    queen_sum_list(Vals, Sum),
    Value is Sum / 100.0.

% Compute dynamic material advantage
dynamic_material_advantage(Board, AdvantageColor, Difference) :-
    dynamic_material_value(Board, white, WhiteVal),
    dynamic_material_value(Board, black, BlackVal),
    (WhiteVal >= BlackVal ->
        AdvantageColor = white,
        Difference is WhiteVal - BlackVal
    ;
        AdvantageColor = black,
        Difference is BlackVal - WhiteVal
    ).



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

`;

// FEN parser in Javascript to convert a chess FEN to Prolog state terms
function parseFenToPrologVars(fen) {
    const fileMap = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8};
    const pieceMap = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'};
    
    try {
        const parts = fen.trim().split(/\s+/);
        if (parts.length === 0 || !parts[0]) return null;
        
        const ranks = parts[0].split('/');
        const prologPieces = [];
        
        for (let rankIdx = 0; rankIdx < ranks.length; rankIdx++) {
            const rankStr = ranks[rankIdx];
            const prologRank = 8 - rankIdx;
            let fileIdx = 1;
            for (let i = 0; i < rankStr.length; i++) {
                const char = rankStr[i];
                if (/\d/.test(char)) {
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
        const parts = fenStr.trim().split(/\s+/);
        if (!parts || parts.length === 0) return null;
        const ranks = parts[0].split('/');
        const fIdx = fm[sq[0]];
        const rIdx = 8 - parseInt(sq[1], 10);
        if (rIdx < 0 || rIdx >= 8 || fIdx < 0 || fIdx >= 8) return null;
        const rStr = ranks[rIdx];
        let currentFile = 0;
        for (let i = 0; i < rStr.length; i++) {
            const char = rStr[i];
            if (/\d/.test(char)) {
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
            explanation = explanation.replace(/\b([1-8])-([1-8])\b/g, (match, xStr, yStr) => {
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
