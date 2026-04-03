"""中国象棋棋盘类

棋子编码约定 (与 AI 项目一致):
  红方 (小写): r=车 n=马 b=相 a=仕 k=帅 c=炮 p=兵
  黑方 (大写): R=車 N=馬 B=象 A=士 K=将 C=砲 P=卒
  空位: '.'

棋盘尺寸: 10 行 × 9 列
"""

# 棋子 -> 中文显示
PIECE_NAMES = {
    # 红方
    "r": "車", "n": "馬", "b": "相", "a": "仕", "k": "帥",
    "c": "炮", "p": "兵",
    # 黑方
    "R": "車", "N": "馬", "B": "象", "A": "士", "K": "將",
    "C": "砲", "P": "卒",
    # 空位
    ".": "．",
}

# 红方棋子集合
RED_PIECES = set("rnbakcp")
# 黑方棋子集合
BLACK_PIECES = set("RNBAKCP")

ROWS = 10
COLS = 9

# 初始棋盘布局
INIT_BOARD = [
    ["R", "N", "B", "A", "K", "A", "B", "N", "R"],  # 0  黑方底线
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # 1
    [".", "C", ".", ".", ".", ".", ".", "C", "."],  # 2  黑炮
    ["P", ".", "P", ".", "P", ".", "P", ".", "P"],  # 3  黑卒
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # 4
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # 5  楚河汉界
    ["p", ".", "p", ".", "p", ".", "p", ".", "p"],  # 6  红兵
    [".", "c", ".", ".", ".", ".", ".", "c", "."],  # 7  红炮
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # 8
    ["r", "n", "b", "a", "k", "a", "b", "n", "r"],  # 9  红方底线
]


class Board:
    """中国象棋棋盘"""

    def __init__(self, board=None):
        if board is not None:
            self.grid = [row[:] for row in board]
        else:
            self.grid = [row[:] for row in INIT_BOARD]

    def __getitem__(self, pos):
        """board[row, col] 方式访问"""
        row, col = pos
        return self.grid[row][col]

    def __setitem__(self, pos, value):
        row, col = pos
        self.grid[row][col] = value

    def piece_at(self, row, col):
        """返回 (row, col) 处的棋子，空位返回 '.'"""
        return self.grid[row][col]

    def is_red(self, row, col):
        return self.grid[row][col] in RED_PIECES

    def is_black(self, row, col):
        return self.grid[row][col] in BLACK_PIECES

    def is_empty(self, row, col):
        return self.grid[row][col] == "."

    # ──────────── 显示 ────────────

    def _piece_display(self, piece):
        """返回棋子的中文显示字符串（带颜色）"""
        name = PIECE_NAMES.get(piece, piece)
        if piece in RED_PIECES:
            # 红色 ANSI
            return f"\033[31m{name}\033[0m"
        elif piece in BLACK_PIECES:
            # 绿色 ANSI
            return f"\033[32m{name}\033[0m"
        else:
            return name

    def display(self):
        """以中文棋子 + 棋盘框线打印棋盘"""
        col_labels = "　".join(
            [str(i) for i in range(COLS)]
        )
        print(f"　　{col_labels}")
        print(f"　　{'─' * (COLS * 2 + COLS - 1)}")

        for row_idx in range(ROWS):
            pieces = "─".join(
                self._piece_display(self.grid[row_idx][col])
                for col in range(COLS)
            )
            print(f" {row_idx} │{pieces}│")

            if row_idx == 4:
                # 楚河汉界
                print(f"　　│{'　' * 2}楚　河　　　汉　界{'　' * 2}│")

        print(f"　　{'─' * (COLS * 2 + COLS - 1)}")

    def display_simple(self):
        """简洁的英文字母显示（调试用）"""
        print("   " + " ".join(str(i) for i in range(COLS)))
        for row_idx in range(ROWS):
            row_str = " ".join(self.grid[row_idx])
            print(f"{row_idx:2d} {row_str}")
            if row_idx == 4:
                print("   " + "= " * COLS + " 楚河汉界")

    def __str__(self):
        """返回简洁棋盘字符串"""
        lines = []
        for row_idx in range(ROWS):
            lines.append(f"{row_idx} " + " ".join(self.grid[row_idx]))
        return "\n".join(lines)


if __name__ == "__main__":
    board = Board()
    print("===== 中文棋盘 =====\n")
    board.display()
    print("\n===== 简洁模式 =====\n")
    board.display_simple()
