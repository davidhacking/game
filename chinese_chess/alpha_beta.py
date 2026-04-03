"""中国象棋 AI — Alpha-Beta 剪枝搜索

评估函数参考 elephantfish 的子力价值和位置表 (PST)。
搜索算法采用经典的 alpha-beta 剪枝，支持自定义搜索深度。

用法:
    from ai import ChessAI
    ai = ChessAI(depth=5)
    move = ai.best_move(board, red_turn=True)  # 返回 ICCS 走法如 'h0h2'
"""

import time
from board import Board, RED_PIECES, BLACK_PIECES, ROWS, COLS

# ────────────────────── 子力基础价值 ──────────────────────
# 参考 elephantfish_improve.py
PIECE_VALUE = {
    "p": 44,  "P": 44,
    "n": 108, "N": 108,
    "b": 23,  "B": 23,
    "r": 233, "R": 233,
    "a": 23,  "A": 23,
    "c": 101, "C": 101,
    "k": 2500, "K": 2500,
}

# ────────────────────── 位置加成表 (10×9) ──────────────────────
# 从 elephantfish 的 16×16 PST 中提取有效区域 (rows 3~12, cols 3~11)
# 这些是黑方视角 (黑方在上 row0, 红方在下 row9)
# 对红方使用时需要上下翻转

# 兵/卒
PST_P = [
    [ 9,  9,  9, 11, 13, 11,  9,  9,  9],  # row0 (elephantfish row3)
    [19, 24, 34, 42, 44, 42, 34, 24, 19],  # row1
    [19, 24, 32, 37, 37, 37, 32, 24, 19],  # row2
    [19, 23, 27, 29, 30, 29, 27, 23, 19],  # row3
    [14, 18, 20, 27, 29, 27, 20, 18, 14],  # row4
    [ 7,  0, 13,  0, 16,  0, 13,  0,  7],  # row5
    [ 7,  0,  7,  0, 15,  0,  7,  0,  7],  # row6
    [ 0,  0,  0,  1,  1,  1,  0,  0,  0],  # row7
    [ 0,  0,  0,  2,  2,  2,  0,  0,  0],  # row8
    [ 0,  0,  0, 11, 15, 11,  0,  0,  0],  # row9
]

# 马
PST_N = [
    [90, 90, 90, 96, 90, 96, 90, 90, 90],
    [90, 96,103, 97, 94, 97,103, 96, 90],
    [92, 98, 99,103, 99,103, 99, 98, 92],
    [93,108,100,107,100,107,100,108, 93],
    [90,100, 99,103,104,103, 99,100, 90],
    [90, 98,101,102,103,102,101, 98, 90],
    [92, 94, 98, 95, 98, 95, 98, 94, 92],
    [93, 92, 94, 95, 92, 95, 94, 92, 93],
    [85, 90, 92, 93, 78, 93, 92, 90, 85],
    [88, 85, 90, 88, 90, 88, 90, 85, 88],
]

# 相/象
PST_B = [
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [ 0, 20,  0,  0,  0, 20,  0,  0,  0],
    [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
    [18,  0,  0, 20, 23, 20,  0,  0, 18],
    [ 0,  0,  0,  0, 23,  0,  0,  0,  0],
    [ 0,  0, 20, 20,  0, 20, 20,  0,  0],
]

# 仕/士 — 与象相同的 PST
PST_A = PST_B

# 车
PST_R = [
    [206,208,207,213,214,213,207,208,206],
    [206,212,209,216,233,216,209,212,206],
    [206,208,207,214,216,214,207,208,206],
    [206,213,213,216,216,216,213,213,206],
    [208,211,211,214,215,214,211,211,208],
    [208,212,212,214,215,214,212,212,208],
    [204,209,204,212,214,212,204,209,204],
    [198,208,204,212,212,212,204,208,198],
    [200,208,206,212,200,212,206,208,200],
    [194,206,204,212,200,212,204,206,194],
]

# 炮
PST_C = [
    [100,100, 96, 91, 90, 91, 96,100,100],
    [ 98, 98, 96, 92, 89, 92, 96, 98, 98],
    [ 97, 97, 96, 91, 92, 91, 96, 97, 97],
    [ 96, 99, 99, 98,100, 98, 99, 99, 96],
    [ 96, 96, 96, 96,100, 96, 96, 96, 96],
    [ 95, 96, 99, 96,100, 96, 99, 96, 95],
    [ 96, 96, 96, 96, 96, 96, 96, 96, 96],
    [ 97, 96,100, 99,101, 99,100, 96, 97],
    [ 96, 97, 98, 98, 98, 98, 98, 97, 96],
    [ 96, 96, 97, 99, 99, 99, 97, 96, 96],
]

# 将/帅 — 使用兵的 PST + K 基础分
PST_K = [[v + PIECE_VALUE["k"] if v > 0 else 0 for v in row] for row in PST_P]

# 按棋子类型查表 (小写 = 棋子类型)
_PST = {
    "p": PST_P,
    "n": PST_N,
    "b": PST_B,
    "a": PST_A,
    "r": PST_R,
    "c": PST_C,
    "k": PST_K,
}

# 极大极小值
INF = 999999

# ────────────────────── 评估函数 ──────────────────────

def evaluate(board):
    """评估局面，返回红方视角的分数（正值红方优，负值黑方优）

    使用子力价值 + 位置加成表 (PST)。
    """
    score = 0
    grid = board.grid
    for r in range(ROWS):
        for c in range(COLS):
            piece = grid[r][c]
            if piece == ".":
                continue
            p = piece.lower()
            pst = _PST[p]
            if piece in RED_PIECES:
                # 红方: 翻转行 (红方底线 row9 对应 PST 的 row0)
                pos_val = pst[9 - r][c]
                score += pos_val
            else:
                # 黑方: 直接使用 (黑方底线 row0 对应 PST 的 row0... 但实际 PST
                # 是从黑方顶端开始的，黑方需要翻转列? 不，elephantfish 的 PST
                # 是从上到下排列，对黑方翻转行)
                # 黑方在 row0~row4，PST 顶部是对手阵地（深入）。
                # 对黑方也要翻转行，让 row0 对应 PST row9。
                pos_val = pst[r][c]
                score -= pos_val
    return score


# ────────────────────── Alpha-Beta 搜索 ──────────────────────

def _flatten_moves(move_dict):
    """将 generate_moves() 返回的字典展开为 (fr, fc, tr, tc) 列表"""
    moves = []
    for (r, c), targets in move_dict.items():
        for tr, tc in targets:
            moves.append((r, c, tr, tc))
    return moves


def _order_moves(board, moves):
    """走法排序: 吃子走法优先（按被吃子价值降序），提高剪枝效率"""
    def move_score(m):
        fr, fc, tr, tc = m
        target = board.grid[tr][tc]
        if target != ".":
            return PIECE_VALUE.get(target, 0)
        return 0
    return sorted(moves, key=move_score, reverse=True)


def _board_key(grid):
    """将棋盘转为不可变的 tuple 用于历史局面查重"""
    return tuple(tuple(row) for row in grid)


def alphabeta(board, depth, alpha, beta, maximizing, nodes_counter=None,
              history=None):
    """Alpha-Beta 剪枝搜索

    Args:
        board: Board 对象
        depth: 搜索深度
        alpha: alpha 值
        beta: beta 值
        maximizing: True = 红方走棋 (最大化), False = 黑方走棋 (最小化)
        nodes_counter: 可选，[int] 用于计数搜索节点
        history: 可选，set 已出现过的局面 key，用于重复检测

    Returns:
        (score, move_iccs) — 评估分数和最佳走法 ICCS 字符串
    """
    if nodes_counter is not None:
        nodes_counter[0] += 1

    # 检查是否有王被吃
    if board._find_king(True) is None:
        return -INF, None
    if board._find_king(False) is None:
        return INF, None

    if depth == 0:
        return evaluate(board), None

    red_turn = maximizing
    move_dict = board.generate_moves(red_turn)
    moves = _flatten_moves(move_dict)

    if not moves:
        # 无棋可走 = 被困毙
        if maximizing:
            return -INF, None
        else:
            return INF, None

    moves = _order_moves(board, moves)

    best_move = None

    if maximizing:
        max_eval = -INF
        for fr, fc, tr, tc in moves:
            # 走棋
            saved_from = board.grid[fr][fc]
            saved_to = board.grid[tr][tc]
            board.grid[tr][tc] = saved_from
            board.grid[fr][fc] = "."

            # 重复局面检测: 走入已出现过的局面给予惩罚
            score = None
            if history is not None:
                key = _board_key(board.grid)
                if key in history:
                    score = -5  # 重复局面惩罚，趋近和棋
            if score is None:
                score, _ = alphabeta(board, depth - 1, alpha, beta, False,
                                     nodes_counter, history)

            # 撤销
            board.grid[fr][fc] = saved_from
            board.grid[tr][tc] = saved_to

            if score > max_eval:
                max_eval = score
                best_move = Board.move_to_iccs(fr, fc, tr, tc)

            alpha = max(alpha, score)
            if beta <= alpha:
                break

        return max_eval, best_move

    else:
        min_eval = INF
        for fr, fc, tr, tc in moves:
            # 走棋
            saved_from = board.grid[fr][fc]
            saved_to = board.grid[tr][tc]
            board.grid[tr][tc] = saved_from
            board.grid[fr][fc] = "."

            # 重复局面检测
            score = None
            if history is not None:
                key = _board_key(board.grid)
                if key in history:
                    score = 5  # 重复局面惩罚，趋近和棋
            if score is None:
                score, _ = alphabeta(board, depth - 1, alpha, beta, True,
                                     nodes_counter, history)

            # 撤销
            board.grid[fr][fc] = saved_from
            board.grid[tr][tc] = saved_to

            if score < min_eval:
                min_eval = score
                best_move = Board.move_to_iccs(fr, fc, tr, tc)

            beta = min(beta, score)
            if beta <= alpha:
                break

        return min_eval, best_move


# ────────────────────── 对外接口 ──────────────────────

class ChessAI:
    """中国象棋 AI 玩家

    封装 alpha-beta 搜索逻辑，提供简洁的对外接口。
    维护历史局面记录，避免重复走子。

    用法:
        ai = ChessAI(depth=5)
        move = ai.best_move(board, red_turn=True)
    """

    def __init__(self, depth=5):
        self.depth = depth
        self.history = set()  # 已出现过的局面

    def best_move(self, board, red_turn):
        """计算最佳走法

        Args:
            board: Board 对象
            red_turn: True = 红方走棋, False = 黑方走棋

        Returns:
            (move_iccs, info) — ICCS 走法字符串, 思考信息字典
            move_iccs 为 None 表示无棋可走
        """
        # 记录当前局面
        self.history.add(_board_key(board.grid))

        nodes = [0]
        t0 = time.time()

        score, move = alphabeta(
            board, self.depth, -INF, INF, red_turn, nodes, self.history
        )

        elapsed = time.time() - t0
        info = {
            "score": score,
            "depth": self.depth,
            "nodes": nodes[0],
            "time": elapsed,
        }
        return move, info
