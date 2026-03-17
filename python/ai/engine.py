import math
import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Optional

from board_utils import (
    BLACK,
    WHITE,
    PASS_MOVE,
    board_full,
    chinese_area_score,
    copy_board,
    legal_moves,
    opponent,
    play_move,
)

BOARD_SIZE = 9
KOMI = 7.5
MCTS_SIMULATIONS = 16
ROLLOUT_MAX_PLIES = 60


@dataclass
class Position:
    board: list
    to_move: int = WHITE
    previous_board: Optional[list] = None
    consecutive_passes: int = 0

    def clone(self) -> "Position":
        return Position(
            board=copy_board(self.board),
            to_move=self.to_move,
            previous_board=copy_board(self.previous_board) if self.previous_board is not None else None,
            consecutive_passes=self.consecutive_passes,
        )

    def legal_moves(self):
        return legal_moves(self.board, self.to_move, self.previous_board, include_pass=True)

    def apply_move(self, move):
        if move == PASS_MOVE:
            return Position(
                board=copy_board(self.board),
                to_move=opponent(self.to_move),
                previous_board=copy_board(self.board),
                consecutive_passes=self.consecutive_passes + 1,
            )

        new_board, ok, _ = play_move(self.board, move, self.to_move, self.previous_board)
        if not ok:
            raise ValueError(f"Illegal move: {move}")
        return Position(
            board=new_board,
            to_move=opponent(self.to_move),
            previous_board=copy_board(self.board),
            consecutive_passes=0,
        )

    def is_terminal(self):
        return self.consecutive_passes >= 2 or board_full(self.board)

    def winner(self):
        score = chinese_area_score(self.board, komi=KOMI)
        if score > 0:
            return BLACK
        if score < 0:
            return WHITE
        return 0


@dataclass
class Node:
    position: Position
    parent: Optional["Node"] = None
    move: Optional[object] = None
    visits: int = 0
    value_sum: float = 0.0
    children: Dict[object, "Node"] = field(default_factory=dict)
    untried_moves: Optional[list] = None

    def __post_init__(self):
        if self.untried_moves is None:
            self.untried_moves = self.position.legal_moves()

    @property
    def q(self) -> float:
        return 0.0 if self.visits == 0 else self.value_sum / self.visits

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def best_child(self, c: float = 1.35) -> "Node":
        best_score = -10**9
        best_node = None
        for child in self.children.values():
            exploit = child.q
            explore = c * math.sqrt(math.log(self.visits + 1) / (child.visits + 1e-9))
            score = exploit + explore
            if score > best_score:
                best_score = score
                best_node = child
        return best_node


def rollout_policy(position: Position):
    legal = position.legal_moves()
    non_pass = [m for m in legal if m != PASS_MOVE]
    if not non_pass:
        return PASS_MOVE

    size = len(position.board)
    center = (size - 1) / 2.0

    def move_score(move):
        x, y = move
        dist = abs(x - center) + abs(y - center)
        adjacency = 0
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < size and 0 <= ny < size and position.board[ny][nx] != 0:
                adjacency += 1
        return adjacency * 3 - dist + random.random() * 0.2

    return max(non_pass, key=move_score)


def simulate(position: Position, root_player: int) -> float:
    current = position.clone()
    plies = 0
    while not current.is_terminal() and plies < ROLLOUT_MAX_PLIES:
        move = rollout_policy(current)
        current = current.apply_move(move)
        plies += 1

    score = chinese_area_score(current.board, komi=KOMI)
    if score == 0:
        return 0.5
    winner = BLACK if score > 0 else WHITE
    return 1.0 if winner == root_player else 0.0


def mcts_best_move(position: Position, simulations: int = MCTS_SIMULATIONS):
    root = Node(position=position)
    root_player = position.to_move

    if root.untried_moves == [PASS_MOVE]:
        return PASS_MOVE

    for _ in range(simulations):
        node = root
        current_position = position.clone()

        while node.is_fully_expanded() and node.children and not current_position.is_terminal():
            node = node.best_child()
            current_position = current_position.apply_move(node.move)

        if not current_position.is_terminal() and node.untried_moves:
            move = random.choice(node.untried_moves)
            node.untried_moves.remove(move)
            current_position = current_position.apply_move(move)
            child = Node(position=current_position, parent=node, move=move)
            node.children[move] = child
            node = child

        result = simulate(current_position, root_player)

        while node is not None:
            node.visits += 1
            node.value_sum += result
            result = 1.0 - result
            node = node.parent

    best_move = PASS_MOVE
    best_visits = -1
    for move, child in root.children.items():
        if child.visits > best_visits:
            best_visits = child.visits
            best_move = move
    return best_move


def get_best_move(board_state):
    """Returns a legal AI move for WHITE on a 9x9 board."""
    position = Position(board=copy_board(board_state), to_move=WHITE)
    move = mcts_best_move(position)
    if move == PASS_MOVE:
        return "pass"
    return [move[0], move[1]]


def play_human_and_ai(board_state, human_move, previous_board_state=None):
    """Apply a BLACK move if legal, then let WHITE reply.

    Returns a dict with the updated board and status text.
    """
    position = Position(
        board=copy_board(board_state),
        to_move=BLACK,
        previous_board=copy_board(previous_board_state) if previous_board_state is not None else None,
    )
    human_move = tuple(human_move)
    after_human_board, ok, reason = play_move(position.board, human_move, BLACK, position.previous_board)
    if not ok:
        return {
            "ok": False,
            "reason": reason,
            "board": copy_board(board_state),
            "ai_move": None,
            "status": f"Illegal move: {reason}",
            "previous_board": copy_board(previous_board_state) if previous_board_state is not None else None,
        }

    after_human = Position(
        board=after_human_board,
        to_move=WHITE,
        previous_board=copy_board(board_state),
        consecutive_passes=0,
    )

    if after_human.is_terminal():
        score = chinese_area_score(after_human.board, komi=KOMI)
        return {
            "ok": True,
            "reason": "game_over",
            "board": after_human.board,
            "ai_move": None,
            "status": f"Game over. Score (Black - White): {score:.1f}",
            "previous_board": copy_board(board_state),
        }

    ai_move = mcts_best_move(after_human)
    if ai_move == PASS_MOVE:
        final_position = after_human.apply_move(PASS_MOVE)
        status = "AI passes. Your turn (Black)"
        return {
            "ok": True,
            "reason": "ok",
            "board": final_position.board,
            "ai_move": "pass",
            "status": status,
            "previous_board": copy_board(after_human.board),
        }

    final_position = after_human.apply_move(ai_move)
    return {
        "ok": True,
        "reason": "ok",
        "board": final_position.board,
        "ai_move": [ai_move[0], ai_move[1]],
        "status": f"AI played at ({ai_move[0]}, {ai_move[1]}). Your turn (Black)",
        "previous_board": copy_board(after_human.board),
    }
