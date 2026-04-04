"""残局模式 AI 对弈测试

验证 AI 能正确在残局局面上进行对弈:
1. 所有残局 FEN 能正确加载
2. 有解法的残局走法序列合法
3. AI 能在每个残局局面上生成合法走法
4. 杀法残局 AI 能赢棋
5. 和棋残局 AI 双方对弈不崩溃
6. 所有残局 (含和棋) AI 对弈不崩溃不死循环
7. FEN 加载正确性抽查
"""

import sys
import time

from board import Board
from alpha_beta import ChessAI
from endgames import ENDGAMES


def test_all_endgames_load():
    """所有残局 FEN 能通过 Board.from_fen 正确加载"""
    for eg in ENDGAMES:
        board, red_first = Board.from_fen(eg["fen"])
        has_red_k = any(board.grid[r][c] == "k" for r in range(10) for c in range(9))
        has_black_k = any(board.grid[r][c] == "K" for r in range(10) for c in range(9))
        assert has_red_k, f"{eg['name']}: 缺少红帅"
        assert has_black_k, f"{eg['name']}: 缺少黑将"


def test_all_endgames_solutions_valid():
    """有解法的残局走法序列合法"""
    tested = 0
    for eg in ENDGAMES:
        if not eg.get("solution"):
            continue
        board, _ = Board.from_fen(eg["fen"])
        red_turn = eg.get("first_move", "red") == "red"
        for i, move in enumerate(eg["solution"]):
            try:
                board.move(move)
            except ValueError as e:
                assert False, f"{eg['name']}: 第{i+1}步 {move} 非法: {e}"
            red_turn = not red_turn
        tested += 1
    assert tested > 0, "没有含解法的残局"


def test_ai_can_move_in_all_endgames():
    """AI 能在每个残局局面上生成合法走法 (包括和棋残局)"""
    ai = ChessAI(depth=2)
    for eg in ENDGAMES:
        board, _ = Board.from_fen(eg["fen"])
        red_turn = eg.get("first_move", "red") == "red"
        move, info = ai.best_move(board, red_turn)
        assert move is not None, f"{eg['name']}: AI 无法生成走法"
        assert len(move) == 4, f"{eg['name']}: AI 走法格式错误: {move}"
        try:
            board.move(move)
        except ValueError as e:
            assert False, f"{eg['name']}: AI 走法 {move} 非法: {e}"


def test_ai_wins_checkmate_endgames():
    """杀法残局: AI 红方能赢棋"""
    checkmate_endgames = [eg for eg in ENDGAMES if eg["category"] == "杀法"]
    assert len(checkmate_endgames) > 0, "没有杀法残局"

    ai_red = ChessAI(depth=5)
    ai_black = ChessAI(depth=2)
    max_moves = 50
    wins = 0

    for eg in checkmate_endgames[:8]:
        board, _ = Board.from_fen(eg["fen"])
        red_turn = eg.get("first_move", "red") == "red"

        for step in range(max_moves):
            if board._find_king(True) is None:
                break
            if board._find_king(False) is None:
                wins += 1
                break
            moves = board.generate_moves(red_turn)
            if sum(len(t) for t in moves.values()) == 0:
                if not red_turn:
                    wins += 1
                break

            ai = ai_red if red_turn else ai_black
            move, _ = ai.best_move(board, red_turn)
            if move is None:
                if not red_turn:
                    wins += 1
                break
            try:
                board.move(move)
            except ValueError:
                break
            red_turn = not red_turn

    assert wins > 0, f"AI 在 {len(checkmate_endgames[:8])} 个杀法残局中未能获胜"


def test_ai_plays_draw_endgames():
    """和棋残局: AI 双方对弈若干步不崩溃"""
    draw_endgames = [eg for eg in ENDGAMES if "和" in eg["name"]]
    if not draw_endgames:
        print("  (没有和棋残局，跳过)")
        return

    ai = ChessAI(depth=3)
    max_moves = 30

    for eg in draw_endgames:
        board, _ = Board.from_fen(eg["fen"])
        red_turn = eg.get("first_move", "red") == "red"
        steps = 0

        for step in range(max_moves):
            if board._find_king(True) is None or board._find_king(False) is None:
                break
            moves = board.generate_moves(red_turn)
            if sum(len(t) for t in moves.values()) == 0:
                break

            move, info = ai.best_move(board, red_turn)
            if move is None:
                break
            try:
                board.move(move)
                steps += 1
            except ValueError:
                assert False, f"{eg['name']}: AI 走法 {move} 在第{step+1}步非法"
            red_turn = not red_turn

        # 和棋残局应该能走多步 (不会1步就结束)
        assert steps >= 2, f"{eg['name']}: 和棋残局只走了 {steps} 步就结束"


def test_ai_plays_all_endgames_no_crash():
    """所有残局 (杀法+基础+定式+古谱): AI 对弈不崩溃不死循环"""
    ai = ChessAI(depth=3)
    max_moves = 30

    for eg in ENDGAMES:
        board, _ = Board.from_fen(eg["fen"])
        red_turn = eg.get("first_move", "red") == "red"

        for step in range(max_moves):
            if board._find_king(True) is None or board._find_king(False) is None:
                break
            moves = board.generate_moves(red_turn)
            if sum(len(t) for t in moves.values()) == 0:
                break

            move, info = ai.best_move(board, red_turn)
            if move is None:
                break
            try:
                board.move(move)
            except ValueError:
                break
            red_turn = not red_turn


def test_endgame_categories_coverage():
    """验证残局覆盖了各个分类"""
    categories = set(eg["category"] for eg in ENDGAMES)
    names_with_draw = [eg["name"] for eg in ENDGAMES if "和" in eg["name"]]
    names_with_solution = [eg["name"] for eg in ENDGAMES if eg.get("solution")]

    assert len(categories) >= 3, f"分类太少: {categories}"
    assert len(names_with_draw) >= 2, f"和棋残局太少: {names_with_draw}"
    assert len(names_with_solution) >= 5, f"含解法残局太少: {len(names_with_solution)}"


def test_endgame_fen_roundtrip():
    """FEN 加载后棋盘状态正确 (关键位置抽查)"""
    eg = next(e for e in ENDGAMES if e["name"] == "双车错杀")
    board, red_first = Board.from_fen(eg["fen"])
    assert red_first is True, "双车错杀应该是红先"
    assert board.grid[9][2] == "r", f"c0 应为红车, 实际: {board.grid[9][2]}"
    assert board.grid[9][6] == "r", f"g0 应为红车, 实际: {board.grid[9][6]}"
    assert board.grid[9][4] == "k", f"e0 应为红帅, 实际: {board.grid[9][4]}"
    assert board.grid[0][4] == "K", f"e9 应为黑将, 实际: {board.grid[0][4]}"


# ──────────── 运行所有测试 ────────────

def run_test(fn):
    name = fn.__name__
    t0 = time.time()
    try:
        fn()
        dt = time.time() - t0
        print(f"  ✓ {name} ({dt:.3f}s)")
        return True
    except Exception as e:
        dt = time.time() - t0
        print(f"  ✗ {name} ({dt:.3f}s): {e}")
        return False


def main():
    print(f"残局 AI 对弈测试 (共 {len(ENDGAMES)} 个残局)\n")

    # 统计分类
    cats = {}
    for eg in ENDGAMES:
        cat = eg["category"]
        cats[cat] = cats.get(cat, 0) + 1
    for cat, cnt in cats.items():
        print(f"  {cat}: {cnt} 个")
    draw_cnt = sum(1 for eg in ENDGAMES if "和" in eg["name"])
    print(f"  其中和棋残局: {draw_cnt} 个\n")

    tests = [
        test_all_endgames_load,
        test_all_endgames_solutions_valid,
        test_ai_can_move_in_all_endgames,
        test_ai_wins_checkmate_endgames,
        test_ai_plays_draw_endgames,
        test_ai_plays_all_endgames_no_crash,
        test_endgame_categories_coverage,
        test_endgame_fen_roundtrip,
    ]
    ok = sum(run_test(t) for t in tests)
    total = len(tests)
    print(f"\n  总计: {total} 个测试, {ok} 通过, {total - ok} 失败")
    if ok < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
