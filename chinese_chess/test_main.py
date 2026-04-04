"""main.py 测试

验证 main.py 的语法正确性和 choose_board 函数逻辑。
"""

import py_compile
import os
import sys

# 确保能导入 chinese_chess 下的模块
sys.path.insert(0, os.path.dirname(__file__))

from unittest.mock import patch


def test_main_syntax():
    """main.py 语法正确，无 IndentationError / SyntaxError"""
    main_path = os.path.join(os.path.dirname(__file__), "main.py")
    # 如果有语法错误会抛出 py_compile.PyCompileError
    py_compile.compile(main_path, doraise=True)


def test_choose_board_full_game():
    """choose_board 选择完整开局返回 (Board, True)"""
    from main import choose_board

    with patch("builtins.input", return_value="1"):
        result = choose_board()
    assert result is not None
    board, red_first = result
    assert red_first is True


def test_choose_board_endgame():
    """choose_board 选择残局(默认)并选第1个残局"""
    from main import choose_board

    # 第一次 input 选 "2"(残局), 第二次 input 选 "1"(第一个残局)
    with patch("builtins.input", side_effect=["2", "1"]):
        result = choose_board()
    assert result is not None
    board, red_first = result
    # 返回的 board 应该不是 None
    assert board is not None


def test_choose_board_quit():
    """choose_board 用户在残局选择界面输入 q 返回 None"""
    from main import choose_board

    with patch("builtins.input", side_effect=["2", "q"]):
        result = choose_board()
    assert result is None


def test_choose_board_eof():
    """choose_board 遇到 EOFError 返回 None"""
    from main import choose_board

    with patch("builtins.input", side_effect=EOFError):
        result = choose_board()
    assert result is None


def test_choose_board_invalid_endgame_index():
    """choose_board 输入无效残局序号返回 None"""
    from main import choose_board

    with patch("builtins.input", side_effect=["2", "999"]):
        result = choose_board()
    assert result is None


def test_fen_valid_endgame():
    """合法的残局 FEN 不报错"""
    from board import Board

    # 高兵胜单王 — 合法
    Board.from_fen("4k4/9/4P4/9/9/9/9/9/9/4K4 w")


def test_fen_bishop_illegal_position():
    """象/相在非法位置应报错"""
    from board import Board

    # 黑象在 c7 (FEN 第3行 col c) — 非法田字位
    try:
        Board.from_fen("4k4/9/2b6/9/9/9/9/9/9/4K4 w")
        assert False, "应抛出 ValueError"
    except ValueError as e:
        assert "黑象" in str(e)


def test_fen_advisor_illegal_position():
    """士/仕在非法位置应报错"""
    from board import Board

    # FEN: 黑士在 e9 (grid[0][4]) — 不是士的合法对角线位置
    # 黑将在 d9 (grid[0][3]) — 在九宫内
    try:
        Board.from_fen("3ka4/9/9/9/9/9/9/9/9/4K4 w")
        assert False, "应抛出 ValueError"
    except ValueError as e:
        assert "黑士" in str(e)


def test_fen_king_outside_palace():
    """将/帅在九宫外应报错"""
    from board import Board

    # 红帅在 a0 — 九宫外
    try:
        Board.from_fen("4k4/9/9/9/9/9/9/9/9/K8 w")
        assert False, "应抛出 ValueError"
    except ValueError as e:
        assert "红帅" in str(e)


def test_fen_pawn_on_own_side():
    """兵在己方区域应报错 (红兵只能在ICCS行3~9)"""
    from board import Board

    # 红兵在 e0 (ICCS行0, 红方底线) — 不合法
    try:
        Board.from_fen("4k4/9/9/9/9/9/9/9/9/4P3K w")
        assert False, "红兵在e0应抛出 ValueError"
    except ValueError as e:
        assert "红兵" in str(e)

    # 红兵在 e2 (ICCS行2, 仍在己方区域) — 不合法
    try:
        Board.from_fen("4k4/9/9/9/9/9/9/4P4/9/4K4 w")
        assert False, "红兵在e2应抛出 ValueError"
    except ValueError as e:
        assert "红兵" in str(e)

    # 红兵在 e3 (ICCS行3, 兵的起始行) — 合法
    Board.from_fen("4k4/9/9/9/9/9/4P4/9/9/4K4 w")

    # 黑卒在 e9 (ICCS行9, 黑方底线) — 不合法
    # FEN: 小写p = 黑卒 (FEN标准: 大写=红, 小写=黑)
    try:
        Board.from_fen("3pk4/9/9/9/9/9/9/9/9/4K4 w")
        assert False, "黑卒在e9应抛出 ValueError"
    except ValueError as e:
        assert "黑卒" in str(e)


if __name__ == "__main__":
    tests = [
        test_main_syntax,
        test_choose_board_full_game,
        test_choose_board_endgame,
        test_choose_board_quit,
        test_choose_board_eof,
        test_choose_board_invalid_endgame_index,
        test_fen_valid_endgame,
        test_fen_bishop_illegal_position,
        test_fen_advisor_illegal_position,
        test_fen_king_outside_palace,
        test_fen_pawn_on_own_side,
    ]
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__doc__.strip()}")
        except Exception as e:
            print(f"  FAIL: {t.__doc__.strip()} — {e}")
            sys.exit(1)
    print(f"\n全部 {len(tests)} 个测试通过!")
