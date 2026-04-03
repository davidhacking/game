"""中国象棋残局题集

经典残局题目，包含 FEN 局面和解法走法序列 (ICCS 格式)。
由 gen_endgames.py 生成并验证。

FEN 格式: 大写=红方(RNBAKCP), 小写=黑方(rnbakcp), w=红先走, b=黑先走
ICCS 坐标: 列 a~i, 行 0~9 (红方底线=0, 黑方底线=9)
"""

ENDGAMES = [
    {
        "name": "双车错杀",
        "category": "杀法",
        "difficulty": 1,
        "fen": "4kab2/4a4/4b4/9/9/9/9/4B4/4A4/2R1KAR2 w",
        "first_move": "red",
        "solution": ["g0g9", "e9d9", "c0c9"],
    },
    {
        "name": "卧槽马杀",
        "category": "杀法",
        "difficulty": 1,
        "fen": "4kab2/4a4/4b4/9/9/9/9/9/3NK4/9 w",
        "first_move": "red",
        "solution": ["d1c3", "e9d9", "c3d5", "d9e9", "d5e7"],
    },
]
