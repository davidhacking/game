"""棋谱下载工具

从 xqbase.com 下载真实的专业棋谱，转换为 ICCS 格式并写入 games.py。

用法:
    uv run python chinese_chess/gen_games.py [数量] [起始gameid]

示例:
    uv run python chinese_chess/gen_games.py 30 135    # 从 gameid=135 开始下载 30 局
    uv run python chinese_chess/gen_games.py            # 默认下载 30 局
"""

import os
import re
import sys
import time
import urllib.request

# xqbase.com 使用 GBK 编码
ENCODING = "gbk"
BASE_URL = "https://www.xqbase.com/xqbase/?gameid="


def fetch_page(gameid):
    """下载指定 gameid 的页面，返回 UTF-8 文本"""
    url = BASE_URL + str(gameid)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return raw.decode(ENCODING, errors="replace")
    except Exception as e:
        print(f"  下载 gameid={gameid} 失败: {e}")
        return None


def parse_game(html, gameid):
    """从 HTML 中解析棋谱信息

    Returns:
        dict with keys: name, event, red, black, result, moves, url
        or None if parsing fails
    """
    # 1. 提取走法 — jsboard("", "H2-E2 H9-G7 ...")
    m = re.search(r'jsboard\("",\s*"([^"]+)"\s*\)', html)
    if not m:
        return None
    raw_moves = m.group(1).strip()
    # 转换: "H2-E2 H9-G7" -> ["h2e2", "h9g7"]
    moves = []
    for token in raw_moves.split():
        token = token.strip()
        if not token:
            continue
        # 格式: X0-X0 (含连字符) 或 X0X0
        cleaned = token.replace("-", "").lower()
        if len(cleaned) == 4:
            moves.append(cleaned)

    if len(moves) < 5:
        return None  # 太短的棋局不要

    # 2. 提取标题 — "<title>湖北 柳大华 先胜 福建 王晓华 - 象棋巫师棋谱仓库</title>"
    title_m = re.search(r"<title>(.+?)\s*-\s*象棋巫师", html)
    title = title_m.group(1).strip() if title_m else f"棋谱 #{gameid}"

    # 3. 解析结果
    result = "*"
    if "先胜" in title:
        result = "1-0"
    elif "先负" in title:
        result = "0-1"
    elif "先和" in title:
        result = "1/2-1/2"

    # 4. 解析红方/黑方名字 — 从标题解析
    # 标题格式: "团队 红方 先胜/先负/先和 团队 黑方"
    red_name = "红方"
    black_name = "黑方"
    result_words = ["先胜", "先负", "先和"]
    for rw in result_words:
        if rw in title:
            parts = title.split(rw)
            if len(parts) == 2:
                red_name = parts[0].strip()
                black_name = parts[1].strip()
            break

    # 5. 提取赛事名称
    event_m = re.search(
        r'<font size="2">(\d{4}年[^<]+(?:赛|杯|战|局)[^<]*)</font>', html
    )
    event_name = event_m.group(1).strip() if event_m else ""

    # 6. 组合名称
    name = title
    if event_name:
        name = f"{event_name} {title}"

    url = BASE_URL + str(gameid)

    return {
        "name": name,
        "event": event_name,
        "red": red_name,
        "black": black_name,
        "result": result,
        "moves": moves,
        "url": url,
    }


def download_games(count=30, start_id=135, max_id=12000):
    """从 xqbase.com 下载棋谱"""
    games = []
    gameid = start_id
    failures = 0

    while len(games) < count and gameid <= max_id:
        print(f"  下载 gameid={gameid} ...", end="", flush=True)
        html = fetch_page(gameid)
        if html is None:
            failures += 1
            if failures > 20:
                print("\n连续失败过多，停止下载")
                break
            gameid += 1
            continue

        game = parse_game(html, gameid)
        if game:
            games.append(game)
            n_moves = len(game["moves"])
            print(f" ✓ {game['red']} vs {game['black']} ({n_moves}步, {game['result']})")
            failures = 0
        else:
            print(" ✗ 解析失败，跳过")

        gameid += 1
        # 礼貌延迟
        time.sleep(0.5)

    return games


def write_games_py(games, output_path="games.py"):
    """将棋谱写入 games.py"""
    with open(output_path, "w") as f:
        f.write('"""中国象棋棋谱集 (ICCS 格式)\n\n')
        f.write("ICCS 坐标: 列 a~i, 行 0~9 (红方底线=0, 黑方底线=9)\n")
        f.write("每个棋谱都经过 test_games.py 验证可以正常运行完毕。\n")
        f.write("棋谱来源: xqbase.com (象棋巫师棋谱仓库)\n")
        f.write("由 gen_games.py 下载并转换。\n")
        f.write('"""\n\n')
        f.write("GAMES = [\n")

        for game in games:
            f.write("    {\n")
            # 转义名称中的引号
            name = game["name"].replace('"', '\\"')
            red = game["red"].replace('"', '\\"')
            black = game["black"].replace('"', '\\"')
            url = game["url"]
            f.write(f'        "name": "{name}",\n')
            f.write(f'        "red": "{red}",\n')
            f.write(f'        "black": "{black}",\n')
            f.write(f'        "result": "{game["result"]}",\n')
            f.write(f'        "url": "{url}",\n')
            f.write('        "moves": [\n')

            moves = game["moves"]
            for j in range(0, len(moves), 2):
                if j + 1 < len(moves):
                    f.write(f'            "{moves[j]}", "{moves[j+1]}",\n')
                else:
                    f.write(f'            "{moves[j]}",\n')

            f.write("        ],\n")
            f.write("    },\n")

        f.write("]\n")

    print(f"\n已写入 {output_path} ({len(games)} 个棋谱)")


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    start_id = int(sys.argv[2]) if len(sys.argv) > 2 else 135

    print(f"从 xqbase.com 下载 {count} 盘棋谱 (起始 gameid={start_id})...\n")
    games = download_games(count=count, start_id=start_id)

    if not games:
        print("未能下载任何棋谱!")
        return

    output = os.path.join(os.path.dirname(__file__), "games.py")
    write_games_py(games, output)

    # 验证
    print("\n验证棋谱...")
    # 需要确保能导入
    sys.path.insert(0, os.path.dirname(__file__))
    # 重新加载模块
    import importlib
    if "games" in sys.modules:
        importlib.reload(sys.modules["games"])
    from games import GAMES
    from board import Board

    ok = 0
    fail = 0
    for i, game in enumerate(GAMES):
        board = Board()
        try:
            for step, move in enumerate(game["moves"], 1):
                board.move(move)
            print(f"  ✓ 棋谱 {i+1}: {game['name'][:40]} ({len(game['moves'])}步)")
            ok += 1
        except Exception as e:
            print(f"  ✗ 棋谱 {i+1}: {game['name'][:40]} 第{step}步 {move} 失败: {e}")
            fail += 1

    print(f"\n验证完成: {ok} 通过, {fail} 失败")


if __name__ == "__main__":
    main()
