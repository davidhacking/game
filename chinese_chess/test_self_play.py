"""AI 自对弈测试

验证 Alpha-Beta 自对弈流程正确性:
- 对弈能正常结束（不崩溃、不死循环）
- 红方在优势局面下能赢
"""

import time

from board import Board
from alpha_beta import ChessAI


def _make_board(layout):
    """从简洁字符串布局创建 Board"""
    grid = []
    for row_str in layout:
        grid.append(list(row_str))
    return Board(grid)


def _play_game(board, red_ai, black_ai, max_moves=200):
    """AI 自对弈，返回 (result, moves_played)

    result: "red" / "black" / "draw"
    """
    red_turn = True
    moves_played = []

    for _ in range(max_moves):
        # 检查将帅是否还在
        if board._find_king(True) is None:
            return "black", moves_played
        if board._find_king(False) is None:
            return "red", moves_played

        # 检查是否无棋可走
        move_dict = board.generate_moves(red_turn)
        total = sum(len(t) for t in move_dict.values())
        if total == 0:
            return ("black" if red_turn else "red"), moves_played

        ai = red_ai if red_turn else black_ai
        move, info = ai.best_move(board, red_turn)
        if move is None:
            return ("black" if red_turn else "red"), moves_played

        board.move(move)
        moves_played.append(move)
        red_turn = not red_turn

    return "draw", moves_played


# ────────────────────── 测试用例 ──────────────────────

def test_self_play_no_crash():
    """初始局面自对弈不崩溃，能正常走完"""
    board = Board()
    red_ai = ChessAI(depth=2)
    black_ai = ChessAI(depth=2)
    result, moves = _play_game(board, red_ai, black_ai, max_moves=50)
    assert len(moves) > 0, "应该至少走了一步"
    assert result in ("red", "black", "draw"), f"结果应为 red/black/draw，得到 {result}"


def test_red_wins_missing_black_rook():
    """黑方少一个车 (只有左车)，红方应该获胜"""
    # 标准开局但去掉黑方右车 (i9 位置)
    layout = [
        "RNBAK.BN.",  # row0: 黑方底线，i9 的车去掉了
        ".........",
        ".C.....C.",  # row2: 黑炮
        "P.P.P.P.P",  # row3: 黑卒
        ".........",
        ".........",
        "p.p.p.p.p",  # row6: 红兵
        ".c.....c.",  # row7: 红炮
        ".........",
        "rnbakabnr",  # row9: 红方底线 (完整)
    ]
    board = _make_board(layout)
    red_ai = ChessAI(depth=3)
    black_ai = ChessAI(depth=3)
    result, moves = _play_game(board, red_ai, black_ai, max_moves=200)
    assert result == "red", (
        f"红方多一个车应该赢，但结果是 {result} (共 {len(moves)} 步)"
    )


def test_red_wins_rook_vs_nothing():
    """简单残局: 红车+帅 vs 黑将，红方必胜"""
    layout = [
        "....K....",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        "r...k....",
    ]
    board = _make_board(layout)
    red_ai = ChessAI(depth=3)
    black_ai = ChessAI(depth=3)
    result, moves = _play_game(board, red_ai, black_ai, max_moves=100)
    assert result == "red", (
        f"红方有车应该赢，但结果是 {result} (共 {len(moves)} 步)"
    )


# ────────────────────── 测试运行器 ──────────────────────

def run_all_tests():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for test_fn in tests:
        name = test_fn.__name__
        try:
            t0 = time.time()
            test_fn()
            print(f"  \u2713 {name} ({time.time()-t0:.3f}s)")
            passed += 1
        except (AssertionError, Exception) as e:
            print(f"  \u2717 {name}: {e}")
            failed += 1
    print(f"\n  总计: {passed+failed} 个测试, {passed} 通过, {failed} 失败")
    return failed == 0


if __name__ == "__main__":
    print("AI 自对弈测试\n")
    exit(0 if run_all_tests() else 1)
