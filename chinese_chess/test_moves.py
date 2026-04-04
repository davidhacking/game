"""中国象棋走法生成测试 (ICCS 格式)

核心方法: Perft (Performance Test)
标准 Perft 值 (初始局面):
  depth 1: 44
  depth 2: 1,920
  depth 3: 79,666
"""

import time

from board import Board, ROWS, COLS, RED_PIECES, BLACK_PIECES, _is_red


def count_moves(board, red):
    moves = board.generate_moves(red)
    return sum(len(targets) for targets in moves.values())


def perft(board, depth, red):
    if depth == 0:
        return 1
    moves = board.generate_moves(red)
    nodes = 0
    for (fr, fc), targets in moves.items():
        piece = board.grid[fr][fc]
        for tr, tc in targets:
            captured = board.grid[tr][tc]
            board.grid[tr][tc] = piece
            board.grid[fr][fc] = "."
            nodes += perft(board, depth - 1, not red)
            board.grid[fr][fc] = piece
            board.grid[tr][tc] = captured
    return nodes


def make_board(layout):
    lines = [line.strip() for line in layout.strip().splitlines() if line.strip()]
    assert len(lines) == 10, f"需要 10 行，得到 {len(lines)}"
    grid = []
    for line in lines:
        row = line.split()
        assert len(row) == 9, f"每行需要 9 列，得到 {len(row)}: {line}"
        grid.append(row)
    return Board(board=grid)


# ═══════════════════ ICCS 坐标测试 ═══════════════════

def test_iccs_conversion():
    """ICCS 坐标转换正确性"""
    # 红帅初始位置: grid[9][4] = ICCS e0
    assert Board.pos_to_iccs(9, 4) == "e0"
    assert Board.iccs_to_pos("e0") == (9, 4)
    # 黑将初始位置: grid[0][4] = ICCS e9
    assert Board.pos_to_iccs(0, 4) == "e9"
    assert Board.iccs_to_pos("e9") == (0, 4)
    # 红炮: grid[7][1] = ICCS b2
    assert Board.pos_to_iccs(7, 1) == "b2"
    assert Board.iccs_to_pos("b2") == (7, 1)
    # 角落: grid[0][0] = ICCS a9, grid[9][8] = ICCS i0
    assert Board.pos_to_iccs(0, 0) == "a9"
    assert Board.pos_to_iccs(9, 8) == "i0"


def test_iccs_move():
    """ICCS 走法: 马八进七 = b0c2"""
    board = Board()
    captured = board.move("b0c2")
    assert captured == "."
    assert board.grid[7][2] == "n"  # 马到了 c2 = grid[7][2]
    assert board.grid[9][1] == "."  # 原位空了


# ═══════════════════ Perft 测试 ═══════════════════

def test_perft_initial_depth1():
    board = Board()
    assert count_moves(board, True) == 44
    assert count_moves(board, False) == 44


def test_perft_initial_depth2():
    board = Board()
    assert perft(board, 2, True) == 1920


def test_perft_initial_depth3():
    board = Board()
    assert perft(board, 3, True) == 79666


def test_symmetry_red_black_initial():
    board = Board()
    assert count_moves(board, True) == count_moves(board, False)


# ═══════════════════ 车 ═══════════════════

def test_rook_open_board():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . r . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    moves = board.generate_moves(red=True)
    assert len(moves.get((5, 4), [])) == 17


def test_rook_blocked():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . p . r . p . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    moves = board.generate_moves(red=True)
    assert len(moves.get((5, 4), [])) == 11


# ═══════════════════ 马 ═══════════════════

def test_knight_center():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . n . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert len(board.generate_moves(True).get((5, 4), [])) == 8


def test_knight_blocked():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . p . . . .
        . . . p n . . . .
        . . . . p . . . .
        . . . . . p . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert len(board.generate_moves(True).get((5, 4), [])) == 2


def test_knight_corner():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        n . . . . k . . .
    """)
    assert len(board.generate_moves(True).get((9, 0), [])) == 2


# ═══════════════════ 象 ═══════════════════

def test_bishop_normal():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . b . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert len(board.generate_moves(True).get((7, 4), [])) == 4


def test_bishop_blocked():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . p . p . . .
        . . . . b . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert len(board.generate_moves(True).get((7, 4), [])) == 2


def test_bishop_no_cross_river():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . b . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert len(board.generate_moves(True).get((5, 4), [])) == 2


# ═══════════════════ 士 ═══════════════════

def test_advisor_center():
    board = make_board("""
        . . . . . K . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . a . . . .
        . . . k . . . . .
    """)
    assert len(board.generate_moves(True).get((8, 4), [])) == 3


def test_advisor_corner():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . a . . k . .
    """)
    assert len(board.generate_moves(True).get((9, 3), [])) == 1


# ═══════════════════ 将/帅 ═══════════════════

def test_king_center_palace():
    """帅在九宫中心, K 不在九宫列范围内 -> 4 步"""
    board = make_board("""
        . . . . . . . . .
        . . . . . . K . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . k . . . .
        . . . . . . . . .
    """)
    # K 在 (1,6) 不在 col 3~5, 不会将帅对面
    assert len(board.generate_moves(True).get((8, 4), [])) == 4


def test_king_center_palace_with_block():
    board = make_board("""
        . . . . K . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . P . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . k . . . .
        . . . . . . . . .
    """)
    assert len(board.generate_moves(True).get((8, 4), [])) == 4


def test_king_corner_palace():
    board = make_board("""
        . . . . . K . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . k . . . . .
        . . . . . . . . .
        . . . . . . . . .
    """)
    assert len(board.generate_moves(True).get((7, 3), [])) == 2


def test_kings_facing_block():
    board = make_board("""
        . . . . K . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . r . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . k . . . .
    """)
    moves = board.generate_moves(red=True)
    for tr, tc in moves.get((5, 4), []):
        assert tc == 4


def test_kings_facing_king_move():
    board = make_board("""
        . . . . K . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . k . . . . .
    """)
    targets = board.generate_moves(True).get((9, 3), [])
    assert (9, 4) not in set(targets)


def test_flying_general():
    board = make_board("""
        . . . . K . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . k . . . .
    """)
    targets = board.generate_moves(True).get((9, 4), [])
    assert (0, 4) in set(targets)


def test_flying_general_blocked():
    board = make_board("""
        . . . . K . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . P . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . k . . . .
    """)
    targets = board.generate_moves(True).get((9, 4), [])
    assert (0, 4) not in set(targets)


# ═══════════════════ 炮 ═══════════════════

def test_cannon_capture_over_mount():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . P . . . .
        . . . . . . . . .
        . . . . p . . . .
        . . . . c . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    targets = set(board.generate_moves(True).get((5, 4), []))
    assert (4, 4) not in targets
    assert (2, 4) in targets


def test_cannon_no_capture_without_mount():
    board = make_board("""
        . . . . K . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . c . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    targets = set(board.generate_moves(True).get((5, 4), []))
    assert (0, 4) not in targets


def test_cannon_two_mounts():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . P . . . .
        . . . . P . . . .
        . . . . P . . . .
        . . . . c . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    targets = set(board.generate_moves(True).get((5, 4), []))
    assert (3, 4) in targets
    assert (2, 4) not in targets


# ═══════════════════ 兵/卒 ═══════════════════

def test_pawn_before_river():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . p . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    targets = board.generate_moves(True).get((6, 4), [])
    assert len(targets) == 1
    assert targets[0] == (5, 4)


def test_pawn_after_river():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . p . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    targets = board.generate_moves(True).get((4, 4), [])
    assert len(targets) == 3


def test_pawn_no_retreat():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . p . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    for tr, tc in board.generate_moves(True).get((3, 4), []):
        assert tr <= 3


def test_black_pawn_symmetry():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . P . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert len(board.generate_moves(False).get((5, 4), [])) == 3


def test_pawn_edge():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        p . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert len(board.generate_moves(True).get((4, 0), [])) == 2


# ═══════════════════ 综合 ═══════════════════

def test_no_friendly_capture():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . r . . . .
        . . . . . k . . .
    """)
    targets = set(board.generate_moves(True).get((8, 4), []))
    assert (9, 5) not in targets


def test_move_and_undo_consistency():
    board = Board()
    import copy
    original = copy.deepcopy(board.grid)
    moves = board.generate_moves(red=True)
    for (fr, fc), targets in moves.items():
        piece = board.grid[fr][fc]
        for tr, tc in targets:
            captured = board.grid[tr][tc]
            board.grid[tr][tc] = piece
            board.grid[fr][fc] = "."
            board.grid[fr][fc] = piece
            board.grid[tr][tc] = captured
    assert board.grid == original


def test_capture_enemy():
    board = make_board("""
        . . . K . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . P . . . .
        . . . . r . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . k . . .
    """)
    assert (4, 4) in set(board.generate_moves(True).get((5, 4), []))


def test_game_over_king_captured():
    board = make_board("""
        . . . . K . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . k . . . .
    """)
    captured = board.move("e0e9")
    assert captured == "K"
    assert board._find_king(False) is None


def test_no_moves_means_lose():
    """将帅都在时，即使被困也有送死走法（困毙不判无棋可走）"""
    board = make_board("""
        . . . r K r . . .
        . . . . r . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . . . . . .
        . . . . k . . . .
    """)
    moves = board.generate_moves(False)
    total = sum(len(t) for t in moves.values())
    # 黑将被困但仍应有走法（送死），游戏通过吃将终局
    assert total > 0, "将帅都在时应有走法（含送死）"


# ═══════════════════ 棋谱走法验证 ═══════════════════

def test_game_replay():
    """验证第一个棋谱前几步能正常走"""
    from games import GAMES
    board = Board()
    game = GAMES[0]
    for iccs_move in game["moves"][:6]:
        board.move(iccs_move)  # 不抛异常即通过


# ═══════════════════ 运行 ═══════════════════

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
    print("中国象棋走法生成测试 (ICCS)\n")
    exit(0 if run_all_tests() else 1)
