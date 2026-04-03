"""棋谱完整性测试

验证 games.py 中的所有棋谱都能正常运行完毕，不出现非法走法。
"""

import time

from board import Board
from games import GAMES


def _run_game(idx, game):
    """测试单个棋谱能否正常运行完"""
    board = Board()
    red_turn = True
    name = game.get("name", f"棋谱{idx+1}")
    url = game.get("url", "")
    for step, iccs_move in enumerate(game["moves"], 1):
        try:
            captured = board.move(iccs_move)
        except ValueError as e:
            url_info = f"\n  来源: {url}" if url else ""
            raise AssertionError(
                f"[{name}] 第 {step} 步 {'红' if red_turn else '黑'} "
                f"{iccs_move} 失败: {e}{url_info}"
            )
        # 将帅被吃则结束
        if captured in ("k", "K"):
            break
        red_turn = not red_turn


def test_all_games():
    """所有棋谱都能正常运行"""
    for i, game in enumerate(GAMES):
        _run_game(i, game)


def test_games_have_moves():
    """每个棋谱至少有 1 步"""
    for i, game in enumerate(GAMES):
        assert len(game["moves"]) > 0, f"棋谱 {i+1} [{game['name']}] 没有走法"


def test_games_have_metadata():
    """每个棋谱有完整的元数据"""
    for i, game in enumerate(GAMES):
        for key in ("name", "red", "black", "result", "moves", "url"):
            assert key in game, f"棋谱 {i+1} 缺少字段 '{key}'"


def test_games_count():
    """至少有 10 个棋谱"""
    assert len(GAMES) >= 10, f"棋谱数量 {len(GAMES)} < 10"


def test_games_have_url():
    """每个棋谱都有来源链接"""
    for i, game in enumerate(GAMES):
        url = game.get("url", "")
        assert url.startswith("http"), (
            f"棋谱 {i+1} [{game['name']}] 缺少有效的 url 字段"
        )


def test_games_result_format():
    """结果格式合法"""
    valid = {"1-0", "0-1", "1/2-1/2", "*"}
    for i, game in enumerate(GAMES):
        assert game["result"] in valid, (
            f"棋谱 {i+1} [{game['name']}] 结果 '{game['result']}' 不合法"
        )


def test_games_moves_format():
    """所有走法都是 4 字符 ICCS 格式"""
    for i, game in enumerate(GAMES):
        for step, move in enumerate(game["moves"], 1):
            assert len(move) == 4, (
                f"棋谱 {i+1} [{game['name']}] 第 {step} 步 '{move}' 不是 4 字符"
            )
            col1, row1, col2, row2 = move[0], move[1], move[2], move[3]
            assert "a" <= col1 <= "i", f"列 '{col1}' 超范围"
            assert "0" <= row1 <= "9", f"行 '{row1}' 超范围"
            assert "a" <= col2 <= "i", f"列 '{col2}' 超范围"
            assert "0" <= row2 <= "9", f"行 '{row2}' 超范围"


def run_all_tests():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for test_fn in tests:
        name = test_fn.__name__
        try:
            t0 = time.time()
            test_fn()
            print(f"  ✓ {name} ({time.time()-t0:.3f}s)")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n  总计: {passed+failed} 个测试, {passed} 通过, {failed} 失败")
    return failed == 0


if __name__ == "__main__":
    print("棋谱完整性测试\n")
    exit(0 if run_all_tests() else 1)
