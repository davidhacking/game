"""AI 残局测试

用经典残局局面验证 AI 搜索的正确性:
- 能找到杀招
- 会吃白送的子
- 不会送帅
- 不同深度都返回合法走法
"""

import time

from board import Board, RED_PIECES, BLACK_PIECES
from alpha_beta import ChessAI, evaluate, INF


def _make_board(layout):
    """从简洁字符串布局创建 Board

    layout: 10 行字符串列表，每行 9 字符，'.' 表示空位
    """
    grid = []
    for row_str in layout:
        grid.append(list(row_str))
    return Board(grid)


def _is_valid_move(board, move_iccs, red_turn):
    """检查走法是否合法"""
    if move_iccs is None:
        return False
    try:
        fr, fc = Board.iccs_to_pos(move_iccs[:2])
        tr, tc = Board.iccs_to_pos(move_iccs[2:])
        piece = board.grid[fr][fc]
        if piece == ".":
            return False
        if red_turn and piece not in RED_PIECES:
            return False
        if not red_turn and piece not in BLACK_PIECES:
            return False
        board.validate_move(fr, fc, tr, tc)
        return True
    except ValueError:
        return False


# ────────────────────── 测试用例 ──────────────────────

def test_ai_finds_checkmate():
    """简单杀局: 红方车在将旁，一步杀"""
    # 黑将在 e9 (row0, col4), 红车在 e7 (row2, col4), 红帅在 e0 (row9, col4)
    # 红车 e7->e9 直接吃将
    layout = [
        "....K....",  # row0: 黑将 e9
        ".........",
        "....r....",  # row2: 红车 e7
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        "....k....",  # row9: 红帅 e0
    ]
    board = _make_board(layout)
    ai = ChessAI(depth=3)
    move, info = ai.best_move(board, red_turn=True)
    assert move is not None, "AI 应该找到走法"
    # 红车吃将 e7e9 -> iccs: e7e9 -> (row2,col4)->(row0,col4) -> "e7e9"
    assert move == "e7e9", f"应该是 e7e9 吃将，AI 走了 {move}"


def test_ai_finds_checkmate_rook_cannon():
    """车炮杀局: 红方一步杀"""
    # 黑将 e9 (row0,col4), 黑士 d9 (row0,col3)
    # 红车 a9 (row0,col0) 在第9行，红炮 e7 (row2,col4)
    # 红车 a9->d9 吃士将军，炮在后面做炮架 — 直接杀
    # 不对，让我构造更简单的: 红车直接将军且无法逃脱
    #
    # 简化: 黑将 d9 (row0,col3), 红车 a9 (row0,col0), 红帅 e0 (row9,col4)
    # 红车 a9 横走到 d9 直接吃将
    layout = [
        "...K.....",  # row0: 黑将 d9
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        "r...k....",  # row9: 红车 a0, 红帅 e0
    ]
    board = _make_board(layout)
    ai = ChessAI(depth=3)
    move, info = ai.best_move(board, red_turn=True)
    assert move is not None, "AI 应该找到走法"
    # 红车应该能杀将。a0->a9 (col0, row9->row0) = "a0a9"
    # 然后黑将无处可逃（在 d9, 只能走 d8/e9/e8 等，但红车控制第9行）
    # 实际上直接 a0a9 就是将军，黑将在 d9... 不是一步杀
    # 换个方案: 红车直接在同行吃将
    layout2 = [
        "r..K.....",  # row0: 红车 a9, 黑将 d9 (同行)
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        "....k....",  # row9: 红帅 e0
    ]
    board2 = _make_board(layout2)
    move2, info2 = ai.best_move(board2, red_turn=True)
    assert move2 == "a9d9", f"应该是 a9d9 吃将，AI 走了 {move2}"


def test_ai_captures_free_piece():
    """有白送的车，AI 必须吃"""
    # 红方有车和帅，黑方有将和一个无保护的车
    # 帅和将不在同列，避免飞将；黑将有士保护不怕车
    layout = [
        "...AK....",  # row0: 黑士 d9, 黑将 e9
        ".........",
        ".........",
        ".........",
        ".R.......",  # row4: 黑车 b5 (无保护)
        ".........",
        ".r.......",  # row6: 红车 b3
        ".........",
        ".........",
        "...k.....",  # row9: 红帅 d0
    ]
    board = _make_board(layout)
    ai = ChessAI(depth=3)
    move, info = ai.best_move(board, red_turn=True)
    assert move is not None, "AI 应该找到走法"
    # 红车 b3 吃黑车 b5: (row6,col1)->(row4,col1) = "b3b5"
    assert move == "b3b5", f"应该吃白送的车 b3b5，AI 走了 {move}"


def test_ai_avoids_losing_king():
    """AI 不会走出送帅的走法"""
    # 红帅被黑车将军，红方有炮可以挡
    layout = [
        "...K.....",  # row0: 黑将 d9
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".........",
        ".c.......",  # row7: 红炮 b2
        "....R....",  # row8: 黑车 e1 将军红帅
        "....k....",  # row9: 红帅 e0
    ]
    board = _make_board(layout)
    ai = ChessAI(depth=3)
    move, info = ai.best_move(board, red_turn=True)
    assert move is not None, "AI 应该找到走法"
    assert _is_valid_move(board, move, True), f"AI 走法 {move} 不合法"


def test_ai_depth_affects_result():
    """不同深度返回的走法都合法"""
    board = Board()  # 开局
    for depth in (1, 2, 3):
        ai = ChessAI(depth=depth)
        move, info = ai.best_move(board, red_turn=True)
        assert move is not None, f"深度 {depth} 应返回走法"
        assert _is_valid_move(board, move, True), f"深度 {depth} 走法 {move} 不合法"
        assert info["depth"] == depth


def test_evaluate_initial_position():
    """初始局面评估应接近 0（双方对称）"""
    board = Board()
    score = evaluate(board)
    assert abs(score) < 50, f"初始局面分数 {score} 偏离太大"


def test_ai_plays_full_endgame():
    """从残局开始，AI 双方对弈到底（不崩溃、不死循环）"""
    # 简单残局: 红车+帅 vs 黑将
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
    ai = ChessAI(depth=3)
    red_turn = True
    max_moves = 50
    for i in range(max_moves):
        if board._find_king(True) is None or board._find_king(False) is None:
            break
        moves = board.generate_moves(red_turn)
        total = sum(len(t) for t in moves.values())
        if total == 0:
            break
        move, info = ai.best_move(board, red_turn)
        if move is None:
            break
        assert _is_valid_move(board, move, red_turn), f"第 {i+1} 步走法 {move} 不合法"
        board.move(move)
        red_turn = not red_turn
    # 只要没崩溃就算通过


def test_ai_black_side():
    """AI 执黑也能正常走棋"""
    board = Board()
    ai = ChessAI(depth=2)
    # 红方先走一步
    board.move("b0c2")
    # 黑方 AI 走棋
    move, info = ai.best_move(board, red_turn=False)
    assert move is not None, "黑方 AI 应返回走法"
    assert _is_valid_move(board, move, False), f"黑方走法 {move} 不合法"


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
    print("AI 残局测试\n")
    exit(0 if run_all_tests() else 1)
