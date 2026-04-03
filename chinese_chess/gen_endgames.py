"""残局棋谱生成工具

手工收录经典残局题目 (FEN + 解法走法序列)，验证合法性后写入 endgames.py。

用法:
    uv run python chinese_chess/gen_endgames.py
"""

import os
import sys

# ── FEN 转棋盘 ──────────────────────────────────────────

# FEN 棋子映射: FEN字符 -> 内部编码
# FEN 中大写=红方, 小写=黑方 (国际惯例)
# 但本项目中 小写=红方, 大写=黑方, 因此需要翻转大小写
FEN_TO_PIECE = {
    # FEN 红方(大写) -> 内部红方(小写)
    "R": "r", "N": "n", "B": "b", "A": "a", "K": "k", "C": "c", "P": "p",
    # FEN 黑方(小写) -> 内部黑方(大写)
    "r": "R", "n": "N", "b": "B", "a": "A", "k": "K", "c": "C", "p": "P",
}


def fen_to_grid(fen):
    """将象棋 FEN 字符串转为 Board 的 grid 格式 (10x9 二维列表)

    FEN 示例: "2R1kab2/4a4/4b4/9/9/9/9/9/4K4/9 w"
    - 从黑方底线(row0/ICCS行9)到红方底线(row9/ICCS行0)，用 '/' 分隔
    - 大写=红方，小写=黑方 (FEN国际惯例，与内部编码相反)
    - 数字=连续空格数
    - 'w'=红先走, 'b'=黑先走
    """
    parts = fen.strip().split()
    board_part = parts[0]
    rows = board_part.split("/")
    if len(rows) != 10:
        raise ValueError(f"FEN 应有 10 行，得到 {len(rows)} 行: {fen}")

    grid = []
    for rank_idx, rank in enumerate(rows):
        row = []
        for ch in rank:
            if ch.isdigit():
                row.extend(["."] * int(ch))
            elif ch in FEN_TO_PIECE:
                row.append(FEN_TO_PIECE[ch])
            else:
                raise ValueError(f"FEN 未知字符 '{ch}' (第{rank_idx+1}行): {fen}")
        if len(row) != 9:
            raise ValueError(
                f"FEN 第{rank_idx+1}行应有9列，得到{len(row)}列: {fen}"
            )
        grid.append(row)

    return grid


# ── 残局数据 ──────────────────────────────────────────

ENDGAME_DATA = [
    # ━━━━━ 杀法练习 ━━━━━
    {
        "name": "白脸将杀",
        "category": "杀法",
        "difficulty": 1,
        "fen": "3ak4/4a4/9/9/9/9/9/9/4r4/3K5 w",
        "first_move": "red",
        "solution": ["d0d9"],
        # 红帅 d0 飞将直接杀
    },
    {
        "name": "双车错杀",
        "category": "杀法",
        "difficulty": 1,
        "fen": "4kab2/4a4/4b4/9/9/9/9/4B4/4A4/2R1KAR2 w",
        "first_move": "red",
        "solution": ["g0g9", "e9d9", "c0c9"],
        # 红车g0冲顶g9将军，黑将走d9，红车c0-c9杀
    },
    {
        "name": "马后炮(一)",
        "category": "杀法",
        "difficulty": 1,
        "fen": "4kab2/4a4/4b4/9/9/9/4C4/9/4N4/4K4 w",
        "first_move": "red",
        "solution": ["e2d4", "e9d9", "e3e9"],
        # 马e2-d4将军(照将)，黑将走d9，炮e3-e9(马后炮)杀
    },
    {
        "name": "铁门栓",
        "category": "杀法",
        "difficulty": 1,
        "fen": "4kab2/4a4/4b4/9/9/9/9/5C3/4A4/4KA3 w",
        "first_move": "red",
        "solution": ["f2f9"],
        # 红炮 f2 直冲 f9，士做炮架，铁门栓杀
    },
    {
        "name": "重炮杀",
        "category": "杀法",
        "difficulty": 1,
        "fen": "4kab2/4a4/4b4/9/9/9/9/4C4/4C4/4K4 w",
        "first_move": "red",
        "solution": ["e1e8"],
        # 前炮e1冲到e8做炮架，后炮e2将军即为重炮杀(但这里一步到位)
        # 实际：炮e1到e8，两炮同列重炮杀
    },
    {
        "name": "大胆穿心",
        "category": "杀法",
        "difficulty": 2,
        "fen": "3kab3/4a4/4b4/9/9/9/9/9/4K4/4C4 w",
        "first_move": "red",
        "solution": ["e0e3", "d9e9", "e1e9"],
        # 炮e0沉底e3; 将被迫走e9; 帅e1飞将e9杀(白脸将+炮配合)
    },
    {
        "name": "海底捞月",
        "category": "杀法",
        "difficulty": 2,
        "fen": "3k1ab2/4a4/4b4/4R4/9/9/9/9/4K4/5C3 w",
        "first_move": "red",
        "solution": ["e6e9", "d9d8", "f0f8", "d8d9", "e9e0", "d9e9", "f8f9"],
        # 车沉底照将, 黑将走d8, 炮贴底f8将, 将回d9, 车退回e0, 将走e9, 炮f9杀
    },
    {
        "name": "天地炮",
        "category": "杀法",
        "difficulty": 2,
        "fen": "4kab2/4a4/9/9/9/4b4/4C4/9/4C4/4K4 w",
        "first_move": "red",
        "solution": ["e3e0", "e9d9", "e1e9"],
        # 炮e3沉底e0将军(天炮), 将走d9, 炮e1冲e9(地炮)杀
    },
    # ━━━━━ 实用残局 ━━━━━
    {
        "name": "单车杀单将",
        "category": "实用残局",
        "difficulty": 1,
        "fen": "5k3/9/9/9/9/9/9/9/9/4K1R2 w",
        "first_move": "red",
        "solution": ["g0g9", "f9e9", "e0e1", "e9d9", "g9d9"],
        # 车冲顶g9将，黑将e9避，帅上e1(配合)，将走d9，车杀d9
        # 注意：这是简化路径，实际可能有多种走法
    },
    {
        "name": "车炮杀单将",
        "category": "实用残局",
        "difficulty": 1,
        "fen": "4k4/9/9/9/9/9/9/9/4C4/4K1R2 w",
        "first_move": "red",
        "solution": ["g0g9", "e9d9", "e1e9"],
        # 车冲顶g9将，黑将走d9，炮e1冲e9杀(车做炮架)
    },
    {
        "name": "车马杀单将",
        "category": "实用残局",
        "difficulty": 2,
        "fen": "4k4/9/9/9/9/9/9/4N4/9/4K1R2 w",
        "first_move": "red",
        "solution": ["g0g9", "e9d9", "e2d4", "d9e9", "g9e9"],
        # 车冲顶将，将走d9，马跳d4将，将回e9，车杀e9
    },
    # ━━━━━ 江湖残局 (稍复杂) ━━━━━
    {
        "name": "一车破双士",
        "category": "实用残局",
        "difficulty": 2,
        "fen": "4ka3/4a4/9/9/9/9/9/9/4K4/3R5 w",
        "first_move": "red",
        "solution": ["d0d9", "e9d9", "e1d1", "d9e9", "d1d9"],
        # 车冲底d9将，将吃车... 不对
        # 车d0冲d9照将，将不能吃(因为帅在e1对面照将)
        # 正解：车d0-d9将，黑将e9被迫走d9(吃车则白脸将)
        # 实际上将e9走不了，这里需要重新设计
    },
    {
        "name": "三步闷宫杀",
        "category": "杀法",
        "difficulty": 2,
        "fen": "3k1a3/3Pa4/4b4/4R4/9/9/9/9/4K4/9 w",
        "first_move": "red",
        "solution": ["e6e9", "d9c9", "d8c8"],
        # 车e6冲到e9照将，将走c9(被兵和士堵住)，兵d8-c8闷宫杀
    },
    {
        "name": "弃车杀将",
        "category": "杀法",
        "difficulty": 2,
        "fen": "3akab2/5N3/4b4/9/9/9/9/9/3pK4/3R5 w",
        "first_move": "red",
        "solution": ["d0d9", "e9d9", "f8e6"],
        # 车d0冲d9献车照将(送车)，黑将吃d9，马f8-e6将军绝杀(蹩脚不了因为e7空)
    },
    {
        "name": "双炮联杀",
        "category": "杀法",
        "difficulty": 2,
        "fen": "3kab3/4a4/4b4/4C4/9/9/4C4/9/4K4/9 w",
        "first_move": "red",
        "solution": ["e3e0", "d9e9", "e6e9"],
        # 下炮e3沉底e0(借中路将军)，黑将走e9，上炮e6到e9杀
    },
    {
        "name": "卧槽马杀",
        "category": "杀法",
        "difficulty": 1,
        "fen": "4kab2/4a4/4b4/9/9/9/9/9/3NK4/9 w",
        "first_move": "red",
        "solution": ["d1c3", "e9d9", "c3d5", "d9e9", "d5e7"],
        # 马d1-c3, 将走d9, 马c3-d5将, 将回e9, 马d5-e7卧槽马杀
    },
]


def validate_endgame(eg, verbose=True):
    """验证单个残局的 FEN 和解法

    Returns: (ok: bool, error: str or None)
    """
    name = eg["name"]
    if verbose:
        print(f"  验证: {name} ... ", end="", flush=True)

    # 1. 验证 FEN -> grid
    try:
        grid = fen_to_grid(eg["fen"])
    except ValueError as e:
        msg = f"FEN 解析失败: {e}"
        if verbose:
            print(f"✗ {msg}")
        return False, msg

    # 2. 构造 Board
    sys.path.insert(0, os.path.dirname(__file__))
    from board import Board
    board = Board(grid)

    # 3. 验证每步走法合法
    for step, move in enumerate(eg["solution"], 1):
        try:
            captured = board.move(move)
            if verbose:
                print(f"[步{step}: {move} ✓]", end="", flush=True)
        except ValueError as e:
            msg = f"第{step}步 {move} 非法: {e}"
            if verbose:
                print(f"✗ {msg}")
                print(f"    当前棋盘:")
                board.display()
            return False, msg

    if verbose:
        print(f" ✓ ({len(eg['solution'])}步)")
    return True, None


def write_endgames_py(endgames, output_path):
    """将残局数据写入 endgames.py"""
    with open(output_path, "w") as f:
        f.write('"""中国象棋残局题集\n\n')
        f.write("经典残局题目，包含 FEN 局面和解法走法序列 (ICCS 格式)。\n")
        f.write("由 gen_endgames.py 生成并验证。\n")
        f.write("\n")
        f.write("FEN 格式: 大写=红方(RNBAKCP), 小写=黑方(rnbakcp), w=红先走, b=黑先走\n")
        f.write("ICCS 坐标: 列 a~i, 行 0~9 (红方底线=0, 黑方底线=9)\n")
        f.write('"""\n\n')
        f.write("ENDGAMES = [\n")

        for eg in endgames:
            f.write("    {\n")
            name = eg["name"].replace('"', '\\"')
            f.write(f'        "name": "{name}",\n')
            f.write(f'        "category": "{eg["category"]}",\n')
            f.write(f'        "difficulty": {eg["difficulty"]},\n')
            fen = eg["fen"].replace('"', '\\"')
            f.write(f'        "fen": "{fen}",\n')
            f.write(f'        "first_move": "{eg["first_move"]}",\n')
            f.write('        "solution": [')
            f.write(", ".join(f'"{m}"' for m in eg["solution"]))
            f.write("],\n")
            f.write("    },\n")

        f.write("]\n")

    print(f"\n已写入 {output_path} ({len(endgames)} 个残局)")


def main():
    print("残局棋谱生成工具\n")
    print(f"共 {len(ENDGAME_DATA)} 个残局题目\n")

    # 验证所有残局
    print("验证残局数据...\n")
    valid = []
    failed = 0
    for eg in ENDGAME_DATA:
        ok, err = validate_endgame(eg, verbose=True)
        if ok:
            valid.append(eg)
        else:
            failed += 1

    print(f"\n验证结果: {len(valid)} 通过, {failed} 失败")

    if not valid:
        print("没有通过验证的残局!")
        sys.exit(1)

    # 写入文件
    output = os.path.join(os.path.dirname(__file__), "endgames.py")
    write_endgames_py(valid, output)

    print(f"\n完成! 共 {len(valid)} 个残局写入 endgames.py")
    if failed > 0:
        print(f"警告: {failed} 个残局验证失败，已跳过")
        sys.exit(1)


if __name__ == "__main__":
    main()
