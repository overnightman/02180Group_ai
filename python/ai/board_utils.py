from collections import deque
from copy import deepcopy
from typing import Iterable, List, Optional, Sequence, Set, Tuple

EMPTY = 0
BLACK = 1
WHITE = 2
PASS_MOVE = "pass"

Coord = Tuple[int, int]
Board = List[List[int]]


def opponent(player: int) -> int:
    return BLACK if player == WHITE else WHITE


def copy_board(board: Sequence[Sequence[int]]) -> Board:
    return [list(row) for row in board]


def board_size(board: Sequence[Sequence[int]]) -> int:
    return len(board)


def neighbors(x: int, y: int, size: int) -> Iterable[Coord]:
    if x > 0:
        yield x - 1, y
    if x + 1 < size:
        yield x + 1, y
    if y > 0:
        yield x, y - 1
    if y + 1 < size:
        yield x, y + 1


def get_group(board: Sequence[Sequence[int]], x: int, y: int) -> Set[Coord]:
    color = board[y][x]
    if color == EMPTY:
        return set()
    size = board_size(board)
    group: Set[Coord] = set()
    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in group:
            continue
        if board[cy][cx] != color:
            continue
        group.add((cx, cy))
        for nx, ny in neighbors(cx, cy, size):
            if board[ny][nx] == color and (nx, ny) not in group:
                stack.append((nx, ny))
    return group


def group_liberties(board: Sequence[Sequence[int]], group: Iterable[Coord]) -> Set[Coord]:
    size = board_size(board)
    liberties: Set[Coord] = set()
    for x, y in group:
        for nx, ny in neighbors(x, y, size):
            if board[ny][nx] == EMPTY:
                liberties.add((nx, ny))
    return liberties


def serialize_board(board: Sequence[Sequence[int]]) -> Tuple[Tuple[int, ...], ...]:
    return tuple(tuple(row) for row in board)


def remove_captured_stones(board: Board, player_just_moved: int) -> int:
    captured = 0
    victim = opponent(player_just_moved)
    size = board_size(board)
    seen: Set[Coord] = set()

    for y in range(size):
        for x in range(size):
            if board[y][x] != victim or (x, y) in seen:
                continue
            group = get_group(board, x, y)
            seen.update(group)
            if not group_liberties(board, group):
                captured += len(group)
                for gx, gy in group:
                    board[gy][gx] = EMPTY
    return captured


def is_suicide(board: Sequence[Sequence[int]], x: int, y: int, player: int) -> bool:
    trial = copy_board(board)
    trial[y][x] = player
    remove_captured_stones(trial, player)
    new_group = get_group(trial, x, y)
    return not group_liberties(trial, new_group)


def play_move(
    board: Sequence[Sequence[int]],
    move,
    player: int,
    previous_board: Optional[Sequence[Sequence[int]]] = None,
):
    """Return (new_board, ok, reason).

    Supports simple ko by comparing against previous_board.
    """
    if move == PASS_MOVE:
        return copy_board(board), True, "pass"

    x, y = move
    size = board_size(board)
    if not (0 <= x < size and 0 <= y < size):
        return copy_board(board), False, "out_of_bounds"
    if board[y][x] != EMPTY:
        return copy_board(board), False, "occupied"
    if is_suicide(board, x, y, player):
        return copy_board(board), False, "suicide"

    new_board = copy_board(board)
    new_board[y][x] = player
    remove_captured_stones(new_board, player)

    if previous_board is not None and serialize_board(new_board) == serialize_board(previous_board):
        return copy_board(board), False, "ko"

    return new_board, True, "ok"


def legal_moves(
    board: Sequence[Sequence[int]],
    player: int,
    previous_board: Optional[Sequence[Sequence[int]]] = None,
    include_pass: bool = True,
):
    size = board_size(board)
    moves = []
    for y in range(size):
        for x in range(size):
            if board[y][x] != EMPTY:
                continue
            _, ok, _ = play_move(board, (x, y), player, previous_board)
            if ok:
                moves.append((x, y))
    if include_pass:
        moves.append(PASS_MOVE)
    return moves


def chinese_area_score(board: Sequence[Sequence[int]], komi: float = 7.5) -> float:
    """Positive means Black leads, negative means White leads."""
    size = board_size(board)
    visited: Set[Coord] = set()
    black_score = 0
    white_score = komi

    for y in range(size):
        for x in range(size):
            cell = board[y][x]
            if cell == BLACK:
                black_score += 1
            elif cell == WHITE:
                white_score += 1
            elif (x, y) not in visited:
                region: Set[Coord] = set()
                bordering: Set[int] = set()
                queue = deque([(x, y)])
                while queue:
                    cx, cy = queue.popleft()
                    if (cx, cy) in visited or board[cy][cx] != EMPTY:
                        continue
                    visited.add((cx, cy))
                    region.add((cx, cy))
                    for nx, ny in neighbors(cx, cy, size):
                        stone = board[ny][nx]
                        if stone == EMPTY and (nx, ny) not in visited:
                            queue.append((nx, ny))
                        elif stone != EMPTY:
                            bordering.add(stone)
                if bordering == {BLACK}:
                    black_score += len(region)
                elif bordering == {WHITE}:
                    white_score += len(region)

    return float(black_score - white_score)


def board_full(board: Sequence[Sequence[int]]) -> bool:
    return all(cell != EMPTY for row in board for cell in row)


def pretty_move(move) -> str:
    return "pass" if move == PASS_MOVE else f"({move[0]}, {move[1]})"
