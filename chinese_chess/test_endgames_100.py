"""残局棋谱完整性测试

验证 endgames.py 中所有残局棋谱:
1. 数量正确
2. 五大分类覆盖完整、数量正确
3. 每局必填字段完整
4. FEN 格式合法 (10 行, 每行 9 列)
5. FEN 棋子字符全部合法
6. 每局至少有将和帅
7. Board.from_fen() 能正常加载所有局面
8. 胜/和标注合法
9. AI 能在所有局面上走出合法走法
10. AI 对弈多步不崩溃
"""

import sys
import time

from board import Board
from endgames import ENDGAMES
from alpha_beta import ChessAI


# ─────────── FEN 字符合法集 ───────────
VALID_FEN_CHARS = set("RNBAKCPrnbakcp123456789")

EXPECTED_CATEGORIES = {
    "兵类": 4,
    "马类": 4,
    "炮类": 4,
    "车类": 6,
    "综合类": 1,
}
EXPECTED_TOTAL = sum(EXPECTED_CATEGORIES.values())  # 19


def test_count():
    """残局总数正确"""
    assert len(ENDGAMES) == EXPECTED_TOTAL, (
        f"残局数量 {len(ENDGAMES)} != {EXPECTED_TOTAL}"
    )


def test_categories_complete():
    """五大分类齐全且数量正确"""
    actual = {}
    for eg in ENDGAMES:
        cat = eg["category"]
        actual[cat] = actual.get(cat, 0) + 1

    for cat, cnt in EXPECTED_CATEGORIES.items():
        assert cat in actual, f"缺少分类: {cat}"
        assert actual[cat] == cnt, (
            f"分类 '{cat}' 数量 {actual[cat]} != 预期 {cnt}"
        )
    for cat in actual:
        assert cat in EXPECTED_CATEGORIES, f"多出意外分类: {cat}"


def test_required_fields():
    """每局都有必填字段"""
    required = ("name", "category", "difficulty", "fen", "first_move", "result", "solution")
    for i, eg in enumerate(ENDGAMES):
        for key in required:
            assert key in eg, f"第 {i+1} 局 [{eg.get('name', '?')}] 缺少字段 '{key}'"


def test_no_duplicate_names():
    """残局名不重复（同分类内不重名）"""
    seen = set()
    dupes = []
    for eg in ENDGAMES:
        key = (eg["name"], eg["category"])
        if key in seen:
            dupes.append(f"{eg['name']} ({eg['category']})")
        seen.add(key)
    assert not dupes, f"存在重复残局: {dupes}"


def test_fen_format():
    """FEN 格式正确: 10 行, 每行恰好 9 列"""
    for i, eg in enumerate(ENDGAMES):
        fen = eg["fen"]
        board_part = fen.split()[0]
        rows = board_part.split("/")
        assert len(rows) == 10, (
            f"第 {i+1} 局 [{eg['name']}] FEN 应有 10 行, 得到 {len(rows)} 行"
        )
        for j, row_str in enumerate(rows):
            cols = 0
            for ch in row_str:
                if ch.isdigit():
                    cols += int(ch)
                else:
                    cols += 1
            assert cols == 9, (
                f"第 {i+1} 局 [{eg['name']}] 第 {j} 行 '{row_str}' = {cols} 列 (应为9)"
            )


def test_fen_chars_valid():
    """FEN 中只包含合法字符"""
    for i, eg in enumerate(ENDGAMES):
        board_part = eg["fen"].split()[0]
        for ch in board_part:
            if ch == "/":
                continue
            assert ch in VALID_FEN_CHARS, (
                f"第 {i+1} 局 [{eg['name']}] FEN 含非法字符 '{ch}'"
            )


def test_fen_has_both_kings():
    """每局 FEN 都有将 (k=黑将) 和帅 (K=红帅)"""
    for i, eg in enumerate(ENDGAMES):
        board_part = eg["fen"].split()[0]
        assert "k" in board_part, f"第 {i+1} 局 [{eg['name']}] FEN 缺少黑将 (k)"
        assert "K" in board_part, f"第 {i+1} 局 [{eg['name']}] FEN 缺少红帅 (K)"


def test_result_valid():
    """result 只能是 '胜' 或 '和'"""
    valid = {"胜", "和"}
    for i, eg in enumerate(ENDGAMES):
        assert eg["result"] in valid, (
            f"第 {i+1} 局 [{eg['name']}] result '{eg['result']}' 不合法"
        )


def test_first_move_is_red():
    """所有局都是红先"""
    for i, eg in enumerate(ENDGAMES):
        assert eg["first_move"] == "red", (
            f"第 {i+1} 局 [{eg['name']}] first_move 应为 'red'"
        )
        assert " w" in eg["fen"], (
            f"第 {i+1} 局 [{eg['name']}] FEN 缺少 ' w' 标志"
        )


def test_board_from_fen_all():
    """Board.from_fen() 能加载全部局面"""
    for i, eg in enumerate(ENDGAMES):
        try:
            board, red_first = Board.from_fen(eg["fen"])
        except Exception as e:
            assert False, f"第 {i+1} 局 [{eg['name']}] from_fen 失败: {e}"
        assert red_first is True, (
            f"第 {i+1} 局 [{eg['name']}] from_fen 返回 red_first=False"
        )


def test_board_pieces_match_fen():
    """Board 加载后棋子数与 FEN 一致"""
    for i, eg in enumerate(ENDGAMES):
        board, _ = Board.from_fen(eg["fen"])
        # 统计 FEN 中棋子数
        fen_pieces = sum(1 for ch in eg["fen"].split()[0] if ch.isalpha())
        # 统计棋盘格子中棋子数
        board_pieces = sum(
            1 for r in range(10) for c in range(9)
            if board.grid[r][c] != "."
        )
        assert fen_pieces == board_pieces, (
            f"第 {i+1} 局 [{eg['name']}] FEN 有 {fen_pieces} 个棋子, "
            f"棋盘有 {board_pieces} 个"
        )


def test_ai_generates_move_all():
    """AI 能在所有局面上生成合法走法"""
    ai = ChessAI(depth=2)
    for i, eg in enumerate(ENDGAMES):
        board, _ = Board.from_fen(eg["fen"])
        move, info = ai.best_move(board, True)
        assert move is not None, (
            f"第 {i+1} 局 [{eg['name']}] AI 无法生成走法"
        )
        assert len(move) == 4, (
            f"第 {i+1} 局 [{eg['name']}] AI 走法 '{move}' 不是 4 字符"
        )
        try:
            board.move(move)
        except ValueError as e:
            assert False, (
                f"第 {i+1} 局 [{eg['name']}] AI 走法 {move} 非法: {e}"
            )


def test_ai_plays_10_moves_no_crash():
    """每局 AI 对弈 10 步不崩溃"""
    ai = ChessAI(depth=2)
    for i, eg in enumerate(ENDGAMES):
        board, _ = Board.from_fen(eg["fen"])
        red_turn = True
        for step in range(10):
            if board._find_king(True) is None or board._find_king(False) is None:
                break
            moves = board.generate_moves(red_turn)
            if sum(len(t) for t in moves.values()) == 0:
                break
            move, _ = ai.best_move(board, red_turn)
            if move is None:
                break
            try:
                board.move(move)
            except ValueError:
                break
            red_turn = not red_turn


def test_ai_never_returns_none_when_moves_exist():
    """核心不变量: 将帅都在 + 有合法走法 → AI 必须返回走法，不能返回 None"""
    ai = ChessAI(depth=3)
    for i, eg in enumerate(ENDGAMES):
        board, _ = Board.from_fen(eg["fen"])
        red_turn = True
        for step in range(20):
            rk = board._find_king(True)
            bk = board._find_king(False)
            if rk is None or bk is None:
                break
            moves = board.generate_moves(red_turn)
            total = sum(len(t) for t in moves.values())
            if total == 0:
                break
            move, info = ai.best_move(board, red_turn)
            side = "红" if red_turn else "黑"
            assert move is not None, (
                f"第 {i+1} 局 [{eg['name']}] 步{step+1} [{side}方] "
                f"有 {total} 个合法走法但 AI 返回 None"
            )
            assert len(move) == 4, (
                f"第 {i+1} 局 [{eg['name']}] 步{step+1} AI 走法 '{move}' 格式错误"
            )
            try:
                board.move(move)
            except ValueError as e:
                assert False, (
                    f"第 {i+1} 局 [{eg['name']}] 步{step+1} AI 走法 {move} 非法: {e}"
                )
            red_turn = not red_turn
        ai.history.clear()


def test_checkmate_high_pawn():
    """高兵困毙 badcase: 红兵e8+红帅d0 → 黑将f9 被困

    黑将虽然所有走法都送死，但应该仍然能走（被迫送吃），
    而不是直接判"无棋可走"。游戏应通过吃将自然终局。
    """
    board = Board()
    for r in range(10):
        for c in range(9):
            board.grid[r][c] = "."
    # 红帅 d0 = (9, 3)
    board.grid[9][3] = "k"
    # 红兵 e8 = (1, 4), 已过河
    board.grid[1][4] = "p"
    # 黑将 f9 = (0, 5)
    board.grid[0][5] = "K"

    # 将帅都在
    assert board._find_king(True) is not None, "红帅应存在"
    assert board._find_king(False) is not None, "黑将应存在"

    # 黑方应有走法（困毙时将被迫走送死棋）
    moves = board.generate_moves(False)
    total = sum(len(t) for t in moves.values())
    assert total > 0, (
        f"将帅都在时黑方应有走法（即使送死），实际 0 步"
    )

    # 黑将走出后应该能被红兵吃掉
    king_pos = board._find_king(False)
    kr, kc = king_pos
    targets = moves.get((kr, kc), [])
    assert len(targets) > 0, "黑将应有至少一个可走位置"


def test_checkmate_not_false_positive():
    """确保正常局面不会误判为困毙: 黑将在 e9 中央，应有多步可走"""
    board = Board()
    for r in range(10):
        for c in range(9):
            board.grid[r][c] = "."
    # 红帅 e0 = (9, 4)
    board.grid[9][4] = "k"
    # 黑将 e9 = (0, 4)
    board.grid[0][4] = "K"
    # 红兵 a5 = (4, 0), 远处不干扰
    board.grid[4][0] = "p"

    # 将帅对面 → 黑将必须离开 e 列
    moves = board.generate_moves(False)
    total = sum(len(t) for t in moves.values())
    assert total > 0, "黑将应有走法 (d9 或 f9)"

    # 如果红帅不在 e 列, 黑将应有更多走法
    board.grid[9][4] = "."
    board.grid[9][3] = "k"  # 红帅移到 d0
    moves = board.generate_moves(False)
    total = sum(len(t) for t in moves.values())
    assert total >= 2, f"黑将至少能走 d9/f9/e8, 实际只有 {total} 步"


# ──────────── 主函数 ────────────

def run_test(fn):
    name = fn.__name__
    t0 = time.time()
    try:
        fn()
        dt = time.time() - t0
        print(f"  \u2713 {name} ({dt:.3f}s)")
        return True
    except Exception as e:
        dt = time.time() - t0
        print(f"  \u2717 {name} ({dt:.3f}s): {e}")
        return False


def main():
    print(f"=== 残局棋谱完整性测试 ===\n")
    print(f"总局数: {len(ENDGAMES)}")
    cats = {}
    for eg in ENDGAMES:
        cats[eg["category"]] = cats.get(eg["category"], 0) + 1
    for cat, cnt in cats.items():
        print(f"  {cat}: {cnt} 局")
    win_cnt = sum(1 for eg in ENDGAMES if eg["result"] == "胜")
    draw_cnt = sum(1 for eg in ENDGAMES if eg["result"] == "和")
    print(f"  红先胜: {win_cnt} 局, 红先和: {draw_cnt} 局\n")

    tests = [
        test_count,
        test_categories_complete,
        test_required_fields,
        test_no_duplicate_names,
        test_fen_format,
        test_fen_chars_valid,
        test_fen_has_both_kings,
        test_result_valid,
        test_first_move_is_red,
        test_board_from_fen_all,
        test_board_pieces_match_fen,
        test_ai_generates_move_all,
        test_ai_plays_10_moves_no_crash,
        test_ai_never_returns_none_when_moves_exist,
        test_checkmate_high_pawn,
        test_checkmate_not_false_positive,
    ]

    ok = sum(run_test(t) for t in tests)
    total = len(tests)
    print(f"\n  总计: {total} 个测试, {ok} 通过, {total - ok} 失败")
    return ok == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
