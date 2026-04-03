"""中国象棋棋盘类

棋子编码约定 (与 AI 项目一致):
  红方 (小写): r=车 n=马 b=相 a=仕 k=帅 c=炮 p=兵
  黑方 (大写): R=車 N=馬 B=象 A=士 K=将 C=砲 P=卒
  空位: '.'

棋盘尺寸: 10 行 × 9 列
坐标系: 横坐标 1~9, 纵坐标 A~J
"""

# 红方棋子集合
RED_PIECES = set("rnbakcp")
# 黑方棋子集合
BLACK_PIECES = set("RNBAKCP")

ROWS = 10
COLS = 9

# 纵坐标标签
ROW_LABELS = [chr(ord("A") + i) for i in range(ROWS)]  # A~J

# 初始棋盘布局
INIT_BOARD = [
    ["R", "N", "B", "A", "K", "A", "B", "N", "R"],  # A  黑方底线
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # B
    [".", "C", ".", ".", ".", ".", ".", "C", "."],  # C  黑炮
    ["P", ".", "P", ".", "P", ".", "P", ".", "P"],  # D  黑卒
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # E
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # F  楚河汉界
    ["p", ".", "p", ".", "p", ".", "p", ".", "p"],  # G  红兵
    [".", "c", ".", ".", ".", ".", ".", "c", "."],  # H  红炮
    [".", ".", ".", ".", ".", ".", ".", ".", "."],  # I
    ["r", "n", "b", "a", "k", "a", "b", "n", "r"],  # J  红方底线
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

    def display(self):
        """以字母打印棋盘，横坐标 1~9，纵坐标 A~J"""
        # 列标题
        print("  " + " ".join(str(i) for i in range(1, COLS + 1)))

        for row_idx in range(ROWS):
            row_str = " ".join(self.grid[row_idx])
            print(f"{ROW_LABELS[row_idx]} {row_str}")
            if row_idx == 4:
                print("  " + "= " * COLS)

    def __str__(self):
        """返回棋盘字符串"""
        lines = ["  " + " ".join(str(i) for i in range(1, COLS + 1))]
        for row_idx in range(ROWS):
            lines.append(f"{ROW_LABELS[row_idx]} " + " ".join(self.grid[row_idx]))
            if row_idx == 4:
                lines.append("  " + "= " * COLS + "楚河汉界")
        return "\n".join(lines)


if __name__ == "__main__":
    board = Board()
    board.display()
