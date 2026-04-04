"""中国象棋棋盘类

棋子编码约定 (与 AI 项目一致):
  红方 (小写): r=车 n=马 b=相 a=仕 k=帅 c=炮 p=兵
  黑方 (大写): R=車 N=馬 B=象 A=士 K=将 C=砲 P=卒
  空位: '.'

棋盘尺寸: 10 行 × 9 列
坐标系: ICCS 格式 — 列 a~i, 行 0~9 (红方底线=0, 黑方底线=9)
  内部 grid[row][col]: row 0=黑方底线(ICCS 行9), row 9=红方底线(ICCS 行0)
  ICCS 行 = 9 - row, ICCS 列 = col
"""

# 红方棋子集合
RED_PIECES = set("rnbakcp")
# 黑方棋子集合
BLACK_PIECES = set("RNBAKCP")

ROWS = 10
COLS = 9

# ICCS 列标签
COL_LABELS = [chr(ord("a") + i) for i in range(COLS)]  # a~i

# 初始棋盘布局
INIT_BOARD = [
    ["R", "N", "B", "A", "K", "A", "B", "N", "R"],  # row0 = ICCS行9 黑方底线
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # row1 = ICCS行8
    [".", "C", ".", ".", ".", ".", ".", "C", "."],  # row2 = ICCS行7 黑炮
    ["P", ".", "P", ".", "P", ".", "P", ".", "P"],  # row3 = ICCS行6 黑卒
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # row4 = ICCS行5
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # row5 = ICCS行4
    ["p", ".", "p", ".", "p", ".", "p", ".", "p"],  # row6 = ICCS行3 红兵
    [".", "c", ".", ".", ".", ".", ".", "c", "."],  # row7 = ICCS行2 红炮
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # row8 = ICCS行1
    ["r", "n", "b", "a", "k", "a", "b", "n", "r"],  # row9 = ICCS行0 红方底线
]


def _is_red(piece):
    return piece in RED_PIECES


def _is_black(piece):
    return piece in BLACK_PIECES


def _same_side(p1, p2):
    return (_is_red(p1) and _is_red(p2)) or (_is_black(p1) and _is_black(p2))


def _in_board(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS


def _in_palace(r, c, piece):
    """检查是否在九宫内"""
    if 3 <= c <= 5:
        if _is_red(piece) and 7 <= r <= 9:
            return True
        if _is_black(piece) and 0 <= r <= 2:
            return True
    return False


def _count_between_orth(grid, r1, c1, r2, c2):
    """计算两个正交位置之间的棋子数（不含端点）"""
    count = 0
    if r1 == r2:
        lo, hi = min(c1, c2) + 1, max(c1, c2)
        for c in range(lo, hi):
            if grid[r1][c] != ".":
                count += 1
    elif c1 == c2:
        lo, hi = min(r1, r2) + 1, max(r1, r2)
        for r in range(lo, hi):
            if grid[r][c1] != ".":
                count += 1
    return count


# 棋子合法位置表 (内部 grid 坐标: row 0=黑底线, row 9=红底线)
_VALID_POSITIONS = {
    # 红仕(a): 九宫对角线5点
    "a": {(7, 3), (7, 5), (8, 4), (9, 3), (9, 5)},
    # 黑士(A): 九宫对角线5点
    "A": {(0, 3), (0, 5), (1, 4), (2, 3), (2, 5)},
    # 红相(b): 田字7点 (红方半场 row 5-9)
    "b": {(5, 2), (5, 6), (7, 0), (7, 4), (7, 8), (9, 2), (9, 6)},
    # 黑象(B): 田字7点 (黑方半场 row 0-4)
    "B": {(0, 2), (0, 6), (2, 0), (2, 4), (2, 8), (4, 2), (4, 6)},
}

# 棋子中文名 (用于错误提示)
_PIECE_NAMES = {
    "r": "红车", "n": "红马", "b": "红相", "a": "红仕", "k": "红帅", "c": "红炮", "p": "红兵",
    "R": "黑车", "N": "黑马", "B": "黑象", "A": "黑士", "K": "黑将", "C": "黑炮", "P": "黑卒",
}


def _validate_piece_positions(grid):
    """校验棋盘上所有棋子是否在合法位置

    检查规则:
    - 将/帅: 必须在九宫内
    - 士/仕: 必须在九宫对角线5个点上
    - 象/相: 必须在己方半场的7个田字点上
    - 兵/卒: 不能在己方底线区域 (未过河前只能前进)
    """
    errors = []
    for row in range(ROWS):
        for col in range(COLS):
            piece = grid[row][col]
            if piece == ".":
                continue

            iccs_col = chr(ord("a") + col)
            iccs_row = 9 - row

            # 将/帅: 九宫检查
            if piece in ("k", "K") and not _in_palace(row, col, piece):
                errors.append(f"{_PIECE_NAMES[piece]}在{iccs_col}{iccs_row}不合法(应在九宫内)")

            # 士/仕、象/相: 查表
            if piece in _VALID_POSITIONS:
                if (row, col) not in _VALID_POSITIONS[piece]:
                    valid_str = ", ".join(
                        f"{chr(ord('a') + c)}{9 - r}" for r, c in sorted(_VALID_POSITIONS[piece])
                    )
                    errors.append(
                        f"{_PIECE_NAMES[piece]}在{iccs_col}{iccs_row}不合法(合法位置: {valid_str})"
                    )

            # 兵/卒: 红兵只能在 ICCS 行3~9 (grid row 0~6)，黑卒只能在 ICCS 行0~6 (grid row 3~9)
            if piece == "p" and row > 6:  # 红兵在 grid row 7-9 (ICCS 行0-2) 不合法
                errors.append(f"{_PIECE_NAMES[piece]}在{iccs_col}{iccs_row}不合法(红兵只能在ICCS行3~9)")
            if piece == "P" and row < 3:  # 黑卒在 grid row 0-2 (ICCS 行7-9) 不合法
                errors.append(f"{_PIECE_NAMES[piece]}在{iccs_col}{iccs_row}不合法(黑卒只能在ICCS行0~6)")

    if errors:
        raise ValueError("FEN 棋子位置不合法:\n  " + "\n  ".join(errors))


class Board:
    """中国象棋棋盘"""

    def __init__(self, board=None):
        if board is not None:
            self.grid = [row[:] for row in board]
        else:
            self.grid = [row[:] for row in INIT_BOARD]

    @classmethod
    def from_fen(cls, fen):
        """从 FEN 字符串创建棋盘

        FEN 标准: 大写=红方, 小写=黑方。
        但本项目内部约定: 小写=红方, 大写=黑方，需要翻转大小写。
        末尾可选 ' w'(红先) 或 ' b'(黑先)。
        返回 (Board, red_first) 元组。
        """
        # FEN字符 -> 内部编码 (大小写翻转)
        fen_to_piece = {
            "R": "r", "N": "n", "B": "b", "A": "a", "K": "k", "C": "c", "P": "p",
            "r": "R", "n": "N", "b": "B", "a": "A", "k": "K", "c": "C", "p": "P",
        }

        parts = fen.strip().split()
        board_part = parts[0]
        red_first = True
        if len(parts) > 1:
            red_first = parts[1].lower() == "w"

        rows = board_part.split("/")
        if len(rows) != ROWS:
            raise ValueError(f"FEN 应有 {ROWS} 行，得到 {len(rows)} 行")

        grid = []
        for row_str in rows:
            row = []
            for ch in row_str:
                if ch.isdigit():
                    row.extend(["."] * int(ch))
                elif ch in fen_to_piece:
                    row.append(fen_to_piece[ch])
                else:
                    raise ValueError(f"FEN 未知字符 '{ch}'")
            if len(row) != COLS:
                raise ValueError(f"FEN 行 '{row_str}' 解析后应有 {COLS} 列，得到 {len(row)} 列")
            grid.append(row)

        _validate_piece_positions(grid)
        return cls(board=grid), red_first

    def __getitem__(self, pos):
        row, col = pos
        return self.grid[row][col]

    def __setitem__(self, pos, value):
        row, col = pos
        self.grid[row][col] = value

    def piece_at(self, row, col):
        return self.grid[row][col]

    def is_red(self, row, col):
        return self.grid[row][col] in RED_PIECES

    def is_black(self, row, col):
        return self.grid[row][col] in BLACK_PIECES

    def is_empty(self, row, col):
        return self.grid[row][col] == "."

    # ──────────── ICCS 坐标 ────────────

    @staticmethod
    def pos_to_iccs(r, c):
        """内部坐标 -> ICCS 字符串, 如 (9, 7) -> 'h0'"""
        return f"{chr(ord('a') + c)}{9 - r}"

    @staticmethod
    def iccs_to_pos(iccs):
        """ICCS 字符串 -> 内部坐标, 如 'h0' -> (9, 7)"""
        iccs = iccs.strip().lower()
        if len(iccs) != 2:
            raise ValueError(f"ICCS 格式错误: '{iccs}'，应为如 'h0'")
        col_char, row_char = iccs[0], iccs[1]
        if not ("a" <= col_char <= "i"):
            raise ValueError(f"列应为 a~i，得到: '{col_char}'")
        if not row_char.isdigit() or not (0 <= int(row_char) <= 9):
            raise ValueError(f"行应为 0~9，得到: '{row_char}'")
        col = ord(col_char) - ord("a")
        row = 9 - int(row_char)
        return row, col

    @staticmethod
    def move_to_iccs(fr, fc, tr, tc):
        """内部坐标走法 -> ICCS 走法字符串, 如 (9,7,7,7) -> 'h0h2'"""
        return Board.pos_to_iccs(fr, fc) + Board.pos_to_iccs(tr, tc)

    # ──────────── 走法合法性校验 ────────────

    def _find_king(self, red):
        target = "k" if red else "K"
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == target:
                    return r, c
        return None

    def _kings_facing(self):
        rk = self._find_king(True)
        bk = self._find_king(False)
        if rk is None or bk is None:
            return False
        if rk[1] != bk[1]:
            return False
        return _count_between_orth(self.grid, rk[0], rk[1], bk[0], bk[1]) == 0

    def validate_move(self, fr, fc, tr, tc):
        """校验走法是否合法，不合法则抛出 ValueError"""
        piece = self.grid[fr][fc]
        target = self.grid[tr][tc]
        p = piece.lower()

        if target != "." and _same_side(piece, target):
            raise ValueError("不能吃自己的棋子")
        if fr == tr and fc == tc:
            raise ValueError("不能原地不动")

        dr, dc = tr - fr, tc - fc

        if p == "r":
            if fr != tr and fc != tc:
                raise ValueError("车只能走直线")
            if _count_between_orth(self.grid, fr, fc, tr, tc) > 0:
                raise ValueError("车不能跳过其他棋子")

        elif p == "n":
            if not ((abs(dr) == 2 and abs(dc) == 1) or (abs(dr) == 1 and abs(dc) == 2)):
                raise ValueError("马走日字")
            if abs(dr) == 2:
                block_r, block_c = fr + dr // 2, fc
            else:
                block_r, block_c = fr, fc + dc // 2
            if self.grid[block_r][block_c] != ".":
                raise ValueError("蹩马腿")

        elif p == "b":
            if abs(dr) != 2 or abs(dc) != 2:
                raise ValueError("象走田字")
            eye_r, eye_c = fr + dr // 2, fc + dc // 2
            if self.grid[eye_r][eye_c] != ".":
                raise ValueError("塞象眼")
            if _is_red(piece) and tr < 5:
                raise ValueError("相不能过河")
            if _is_black(piece) and tr > 4:
                raise ValueError("象不能过河")

        elif p == "a":
            if abs(dr) != 1 or abs(dc) != 1:
                raise ValueError("士斜走一格")
            if not _in_palace(tr, tc, piece):
                raise ValueError("士不能出九宫")

        elif p == "k":
            opp_king = "K" if _is_red(piece) else "k"
            if target == opp_king and fc == tc:
                if _count_between_orth(self.grid, fr, fc, tr, tc) != 0:
                    raise ValueError("飞将需要同列且中间无子")
            else:
                if not ((abs(dr) == 1 and dc == 0) or (dr == 0 and abs(dc) == 1)):
                    raise ValueError("将/帅直走一格")
                if not _in_palace(tr, tc, piece):
                    raise ValueError("将/帅不能出九宫")

        elif p == "c":
            if fr != tr and fc != tc:
                raise ValueError("炮只能走直线")
            between = _count_between_orth(self.grid, fr, fc, tr, tc)
            if target == ".":
                if between > 0:
                    raise ValueError("炮不吃子时不能跳过棋子")
            else:
                if between != 1:
                    raise ValueError("炮吃子必须隔一个棋子(翻山)")

        elif p == "p":
            if abs(dr) + abs(dc) != 1:
                raise ValueError("兵/卒每步只走一格")
            if _is_red(piece):
                if dr > 0:
                    raise ValueError("兵不能后退")
                if fr > 4 and dc != 0:
                    raise ValueError("兵过河前只能前进")
            else:
                if dr < 0:
                    raise ValueError("卒不能后退")
                if fr < 5 and dc != 0:
                    raise ValueError("卒过河前只能前进")

        # 走完后检查
        red = _is_red(piece)
        saved_from = self.grid[fr][fc]
        saved_to = self.grid[tr][tc]
        self.grid[tr][tc] = piece
        self.grid[fr][fc] = "."
        illegal = self._is_in_check(red) or self._kings_facing()
        self.grid[fr][fc] = saved_from
        self.grid[tr][tc] = saved_to
        if illegal:
            # 困毙时允许将/帅走送死棋（让对方吃掉自然终局）
            if p == "k":
                # 检查该方是否有任何不送死的走法
                has_safe = False
                for r2 in range(ROWS):
                    for c2 in range(COLS):
                        pc2 = self.grid[r2][c2]
                        if pc2 == "." or (red and pc2 not in RED_PIECES) or (not red and pc2 not in BLACK_PIECES):
                            continue
                        for tr2, tc2 in self._candidates(r2, c2):
                            if self._is_legal_after_move(r2, c2, tr2, tc2, pc2, red):
                                has_safe = True
                                break
                        if has_safe:
                            break
                    if has_safe:
                        break
                if not has_safe:
                    return  # 困毙，允许将/帅走送死棋
            raise ValueError("走后被将军或将帅对面")

    # ──────────── 走法生成 ────────────

    def _candidates(self, fr, fc):
        piece = self.grid[fr][fc]
        p = piece.lower()
        grid = self.grid
        results = []

        if p == "r":
            for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                r, c = fr + dr, fc + dc
                while 0 <= r < ROWS and 0 <= c < COLS:
                    t = grid[r][c]
                    if t == ".":
                        results.append((r, c))
                    else:
                        if not _same_side(piece, t):
                            results.append((r, c))
                        break
                    r += dr
                    c += dc

        elif p == "n":
            for leg_dr, leg_dc, moves in (
                (-1, 0, [(-2, -1), (-2, 1)]),
                (1, 0, [(2, -1), (2, 1)]),
                (0, -1, [(-1, -2), (1, -2)]),
                (0, 1, [(-1, 2), (1, 2)]),
            ):
                br, bc = fr + leg_dr, fc + leg_dc
                if not (0 <= br < ROWS and 0 <= bc < COLS):
                    continue
                if grid[br][bc] != ".":
                    continue
                for dr, dc in moves:
                    tr, tc = fr + dr, fc + dc
                    if 0 <= tr < ROWS and 0 <= tc < COLS:
                        t = grid[tr][tc]
                        if t == "." or not _same_side(piece, t):
                            results.append((tr, tc))

        elif p == "b":
            for dr, dc in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
                tr, tc = fr + dr, fc + dc
                if not (0 <= tr < ROWS and 0 <= tc < COLS):
                    continue
                if _is_red(piece) and tr < 5:
                    continue
                if _is_black(piece) and tr > 4:
                    continue
                er, ec = fr + dr // 2, fc + dc // 2
                if grid[er][ec] != ".":
                    continue
                t = grid[tr][tc]
                if t == "." or not _same_side(piece, t):
                    results.append((tr, tc))

        elif p == "a":
            for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                tr, tc = fr + dr, fc + dc
                if _in_palace(tr, tc, piece):
                    t = grid[tr][tc]
                    if t == "." or not _same_side(piece, t):
                        results.append((tr, tc))

        elif p == "k":
            for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                tr, tc = fr + dr, fc + dc
                if _in_palace(tr, tc, piece):
                    t = grid[tr][tc]
                    if t == "." or not _same_side(piece, t):
                        results.append((tr, tc))
            opp_pos = self._find_king(not _is_red(piece))
            if opp_pos and opp_pos[1] == fc:
                opp_r, opp_c = opp_pos
                if _count_between_orth(grid, fr, fc, opp_r, opp_c) == 0:
                    results.append(opp_pos)

        elif p == "c":
            for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                r, c = fr + dr, fc + dc
                while 0 <= r < ROWS and 0 <= c < COLS:
                    if grid[r][c] == ".":
                        results.append((r, c))
                    else:
                        break
                    r += dr
                    c += dc
                r += dr
                c += dc
                while 0 <= r < ROWS and 0 <= c < COLS:
                    t = grid[r][c]
                    if t != ".":
                        if not _same_side(piece, t):
                            results.append((r, c))
                        break
                    r += dr
                    c += dc

        elif p == "p":
            if _is_red(piece):
                dirs = [(-1, 0)]
                if fr < 5:
                    dirs += [(0, -1), (0, 1)]
            else:
                dirs = [(1, 0)]
                if fr > 4:
                    dirs += [(0, -1), (0, 1)]
            for dr, dc in dirs:
                tr, tc = fr + dr, fc + dc
                if 0 <= tr < ROWS and 0 <= tc < COLS:
                    t = grid[tr][tc]
                    if t == "." or not _same_side(piece, t):
                        results.append((tr, tc))

        return results

    def _is_in_check(self, red):
        king_pos = self._find_king(red)
        if king_pos is None:
            return True
        kr, kc = king_pos
        opp_side = BLACK_PIECES if red else RED_PIECES
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] in opp_side:
                    for tr, tc in self._candidates(r, c):
                        if tr == kr and tc == kc:
                            return True
        return False

    def _is_legal_after_move(self, fr, fc, tr, tc, piece, red):
        grid = self.grid
        saved_to = grid[tr][tc]
        grid[tr][tc] = piece
        grid[fr][fc] = "."
        legal = not self._is_in_check(red) and not self._kings_facing()
        grid[fr][fc] = piece
        grid[tr][tc] = saved_to
        return legal

    def generate_moves(self, red):
        side = RED_PIECES if red else BLACK_PIECES
        all_moves = {}
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.grid[r][c]
                if piece not in side:
                    continue
                targets = []
                for tr, tc in self._candidates(r, c):
                    if self._is_legal_after_move(r, c, tr, tc, piece, red):
                        targets.append((tr, tc))
                if targets:
                    all_moves[(r, c)] = targets

        # 只要将/帅还在棋盘上，就不能判"无棋可走"。
        # 若所有走法都会被将军（困毙），则放开将/帅的全部候选走法
        # （包括送吃），让对方通过吃将/帅来自然终局。
        if not all_moves:
            king_pos = self._find_king(red)
            if king_pos is not None:
                kr, kc = king_pos
                king_piece = self.grid[kr][kc]
                king_targets = []
                for tr, tc in self._candidates(kr, kc):
                    target = self.grid[tr][tc]
                    if target == "." or not _same_side(king_piece, target):
                        king_targets.append((tr, tc))
                if king_targets:
                    all_moves[(kr, kc)] = king_targets

        return all_moves

    def display_moves(self, red):
        """打印指定方所有可走棋步的表格（带编号，ICCS 格式）"""
        moves = self.generate_moves(red)
        side_name = "红方" if red else "黑方"
        if not moves:
            print(f"  {side_name}无棋可走!")
            return []

        piece_cn = {
            "r": "车", "n": "马", "b": "相", "a": "仕", "k": "帅", "c": "炮", "p": "兵",
            "R": "車", "N": "馬", "B": "象", "A": "士", "K": "将", "C": "砲", "P": "卒",
        }

        move_list = []
        for (r, c), targets in sorted(moves.items()):
            for tr, tc in targets:
                move_list.append(self.move_to_iccs(r, c, tr, tc))

        print(f"  {side_name}可走棋步:")
        print(f"  {'序号':<6} {'棋子':<4} 走法")
        print(f"  {'─' * 30}")
        idx = 1
        for (r, c), targets in sorted(moves.items()):
            piece = self.grid[r][c]
            name = piece_cn.get(piece, piece)
            for tr, tc in targets:
                iccs = self.move_to_iccs(r, c, tr, tc)
                print(f"  {idx:<6} {name:<4} {iccs}")
                idx += 1

        return move_list

    # ──────────── 走棋 ────────────

    def move(self, iccs_move):
        """走一步棋 (ICCS 格式, 如 'b0c2')

        Returns:
            captured: 被吃掉的棋子，没有则返回 '.'
        """
        iccs_move = iccs_move.strip().lower()
        if len(iccs_move) != 4:
            raise ValueError(f"走法格式错误: '{iccs_move}'，应为 4 字符如 'b0c2'")
        fr, fc = self.iccs_to_pos(iccs_move[:2])
        tr, tc = self.iccs_to_pos(iccs_move[2:])

        piece = self.grid[fr][fc]
        if piece == ".":
            raise ValueError(f"起点 {iccs_move[:2]} 没有棋子")

        self.validate_move(fr, fc, tr, tc)

        captured = self.grid[tr][tc]
        self.grid[tr][tc] = piece
        self.grid[fr][fc] = "."
        return captured

    # ──────────── 显示 ────────────

    def display(self):
        """打印棋盘 (ICCS 坐标: 列 a~i, 行 9~0)"""
        print("  " + " ".join(COL_LABELS))
        for row_idx in range(ROWS):
            iccs_row = 9 - row_idx
            row_str = " ".join(self.grid[row_idx])
            print(f"{iccs_row} {row_str}")
            if row_idx == 4:
                print("  " + "= " * COLS)

    def __str__(self):
        lines = ["  " + " ".join(COL_LABELS)]
        for row_idx in range(ROWS):
            iccs_row = 9 - row_idx
            lines.append(f"{iccs_row} " + " ".join(self.grid[row_idx]))
            if row_idx == 4:
                lines.append("  " + "= " * COLS)
        return "\n".join(lines)
