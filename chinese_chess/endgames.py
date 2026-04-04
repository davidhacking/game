"""中国象棋残局题集（20 局・红先）

经典残局题目，包含 FEN 局面 (ICCS 格式)。
分为五大类：兵类、马类、炮类、车类、综合类。

FEN 格式: 大写=红方(RNBAKCP), 小写=黑方(rnbakcp), w=红先走, b=黑先走
ICCS 坐标: 列 a~i, 行 0~9 (红方底线=0, 黑方底线=9)
"""

ENDGAMES = [
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 一、兵类（步步为营）1-4
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {
        "name": "高兵胜单王",
        "category": "兵类",
        "difficulty": 1,
        "fen": "4k4/9/4P4/9/9/9/9/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "底兵胜单王",
        "category": "兵类",
        "difficulty": 1,
        "fen": "4k4/4P4/9/9/9/9/9/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "双高兵胜单缺象",
        "category": "兵类",
        "difficulty": 1,
        "fen": "4k4/9/4b4/4P1P2/9/9/9/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "三高兵胜士象全",
        "category": "兵类",
        "difficulty": 2,
        "fen": "2bakab2/9/9/2P1P1P2/9/9/9/9/4A4/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 二、马类（八面威风）5-8
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {
        "name": "单马擒单士",
        "category": "马类",
        "difficulty": 1,
        "fen": "4ka3/9/9/9/9/9/4N4/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "马擒单象",
        "category": "马类",
        "difficulty": 1,
        "fen": "4k4/9/4b4/9/9/9/4N4/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "马底兵胜单士象",
        "category": "马类",
        "difficulty": 2,
        "fen": "3ak1b2/4P4/9/5N3/9/9/9/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "双马胜士象全",
        "category": "马类",
        "difficulty": 2,
        "fen": "2bakab2/9/9/9/9/2N1N4/9/9/4A4/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 三、炮类（隔山打牛）9-12
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {
        "name": "炮仕胜单士",
        "category": "炮类",
        "difficulty": 1,
        "fen": "4ka3/9/9/9/9/9/2C6/9/4A4/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "炮高兵胜单象",
        "category": "炮类",
        "difficulty": 1,
        "fen": "4k4/9/4b4/4P4/2C6/9/9/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "炮兵胜单士象",
        "category": "炮类",
        "difficulty": 2,
        "fen": "3ak1b2/9/9/4P4/2C6/9/9/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "双炮胜单士象",
        "category": "炮类",
        "difficulty": 2,
        "fen": "3ak1b2/9/9/2C1C4/9/9/9/9/9/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 四、车类（一车十子寒）13-18
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {
        "name": "单车胜单马",
        "category": "车类",
        "difficulty": 1,
        "fen": "4k4/9/4n4/9/9/9/9/9/2R6/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "单车胜单炮",
        "category": "车类",
        "difficulty": 1,
        "fen": "4k4/9/4c4/9/9/9/9/9/2R6/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "单车胜双士",
        "category": "车类",
        "difficulty": 1,
        "fen": "3a1a3/4k4/9/9/9/9/9/9/2R6/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "单车胜双象",
        "category": "车类",
        "difficulty": 1,
        "fen": "2b1k1b2/9/9/9/9/9/9/9/2R6/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "车兵胜单车",
        "category": "车类",
        "difficulty": 2,
        "fen": "4k4/4r4/9/4P4/9/9/9/9/2R6/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    {
        "name": "车兵胜士象全",
        "category": "车类",
        "difficulty": 2,
        "fen": "2bakab2/9/9/4P4/9/9/9/9/2R6/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 五、综合类 19-20
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {
        "name": "马炮胜士象全",
        "category": "综合类",
        "difficulty": 2,
        "fen": "2bakab2/9/9/9/2N1C4/9/9/9/4A4/4K4 w",
        "first_move": "red",
        "result": "胜",
        "solution": [],
    },
]
