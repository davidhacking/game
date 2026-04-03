"""中国象棋 CLI

模式:
  1. 对弈模式 — 双人轮流走棋
  2. 棋谱模式 — 查看经典棋谱，按 Enter 逐步播放
  3. 人机对弈 — 与 AI 对弈 (Alpha-Beta 剪枝搜索)
  4. AI 自对弈 — Alpha-Beta 红方 vs 黑方自动对弈
"""

import sys
from board import Board
from games import GAMES
from alpha_beta import ChessAI


def check_game_over(board, red_turn):
    """检查游戏是否结束"""
    if board._find_king(True) is None:
        print("\n  === 黑方胜! (帅被吃) ===")
        return True
    if board._find_king(False) is None:
        print("\n  === 红方胜! (将被吃) ===")
        return True
    moves = board.generate_moves(red_turn)
    total = sum(len(t) for t in moves.values())
    if total == 0:
        winner = "红方" if not red_turn else "黑方"
        loser = "黑方" if not red_turn else "红方"
        print(f"\n  === {winner}胜! ({loser}无棋可走) ===")
        return True
    return False


def play_mode():
    """对弈模式"""
    board = Board()
    board.display()
    last_move_list = None
    red_turn = True

    while True:
        if check_game_over(board, red_turn):
            break

        side = "红方" if red_turn else "黑方"
        try:
            cmd = input(f"\n{side}走棋 (ICCS如b0c2, h/H=提示, 编号=选走法, q=退出): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if cmd.lower() in ("q", "quit", "exit"):
            break

        if cmd == "h":
            last_move_list = board.display_moves(red=True)
            continue
        if cmd == "H":
            last_move_list = board.display_moves(red=False)
            continue

        # 编号选择
        if cmd.isdigit() and last_move_list:
            idx = int(cmd)
            if 1 <= idx <= len(last_move_list):
                cmd = last_move_list[idx - 1]
            else:
                print(f"编号超出范围 (1~{len(last_move_list)})")
                continue

        cmd = cmd.lower()
        if len(cmd) != 4:
            print("格式错误，请输入 ICCS 走法如 b0c2，或先按 h 再输入编号")
            continue

        try:
            captured = board.move(cmd)
            last_move_list = None
            print()
            board.display()
            if captured != ".":
                print(f"  吃掉: {captured}")
            red_turn = not red_turn
        except ValueError as e:
            print(f"错误: {e}")


def replay_mode():
    """棋谱模式"""
    print("\n经典棋谱列表:")
    print(f"  {'序号':<4} {'名称':<20} {'红方':<10} {'黑方':<10} 结果")
    print(f"  {'─' * 60}")
    for i, game in enumerate(GAMES, 1):
        print(f"  {i:<4} {game['name']:<20} {game['red']:<10} {game['black']:<10} {game['result']}")

    try:
        choice = input("\n输入棋谱序号 (q=返回): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.lower() in ("q", "quit", "exit"):
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(GAMES)):
        print(f"无效序号，应为 1~{len(GAMES)}")
        return

    game = GAMES[int(choice) - 1]
    print(f"\n  《{game['name']}》")
    print(f"  红方: {game['red']}  黑方: {game['black']}  结果: {game['result']}")
    print(f"  共 {len(game['moves'])} 步\n")

    board = Board()
    board.display()

    red_turn = True
    for step, iccs_move in enumerate(game["moves"], 1):
        side = "红" if red_turn else "黑"
        try:
            cmd = input(f"\n第 {step} 步 [{side}] {iccs_move} (Enter=下一步, q=退出): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出棋谱")
            return

        if cmd.lower() in ("q", "quit", "exit"):
            return

        try:
            captured = board.move(iccs_move)
            print()
            board.display()
            if captured != ".":
                print(f"  吃掉: {captured}")
        except ValueError as e:
            print(f"  走法错误: {e} (棋谱可能有误)")
            return

        red_turn = not red_turn

    print(f"\n  棋谱结束! 结果: {game['result']}")


def ai_mode():
    """人机对弈模式"""
    # 选择执红/执黑
    print("\n选择执子方:")
    print("  1. 执红 (先手)")
    print("  2. 执黑 (后手)")
    try:
        side_choice = input("选择 (默认1): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    human_is_red = side_choice != "2"
    human_side = "红方" if human_is_red else "黑方"
    ai_side = "黑方" if human_is_red else "红方"

    # 选择搜索深度
    try:
        depth_input = input("AI 搜索深度 (1~8, 默认5): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    depth = 5
    if depth_input.isdigit() and 1 <= int(depth_input) <= 8:
        depth = int(depth_input)

    ai = ChessAI(depth=depth)
    print(f"\n  你执{human_side}, AI 执{ai_side}, 搜索深度={depth}")

    board = Board()
    board.display()
    last_move_list = None
    red_turn = True

    while True:
        if check_game_over(board, red_turn):
            break

        is_human_turn = (red_turn == human_is_red)
        side = "红方" if red_turn else "黑方"

        if not is_human_turn:
            # AI 走棋
            print(f"\n  {ai_side} AI 思考中...")
            move, info = ai.best_move(board, red_turn)
            if move is None:
                print(f"\n  === AI 无棋可走，{'红方' if human_is_red else '黑方'}胜! ===")
                break
            print(f"  AI 走法: {move}  (深度={info['depth']}, "
                  f"节点={info['nodes']}, 耗时={info['time']:.2f}s, "
                  f"评分={info['score']})")
            try:
                captured = board.move(move)
                print()
                board.display()
                if captured != ".":
                    print(f"  吃掉: {captured}")
            except ValueError as e:
                print(f"  AI 走法错误: {e}")
                break
            red_turn = not red_turn
            continue

        # 人类走棋
        try:
            cmd = input(f"\n{side}走棋 (ICCS如b0c2, h=提示, 编号=选走法, q=退出): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if cmd.lower() in ("q", "quit", "exit"):
            break

        if cmd.lower() == "h":
            last_move_list = board.display_moves(red=red_turn)
            continue

        # 编号选择
        if cmd.isdigit() and last_move_list:
            idx = int(cmd)
            if 1 <= idx <= len(last_move_list):
                cmd = last_move_list[idx - 1]
            else:
                print(f"编号超出范围 (1~{len(last_move_list)})")
                continue

        cmd = cmd.lower()
        if len(cmd) != 4:
            print("格式错误，请输入 ICCS 走法如 b0c2，或先按 h 再输入编号")
            continue

        try:
            captured = board.move(cmd)
            last_move_list = None
            print()
            board.display()
            if captured != ".":
                print(f"  吃掉: {captured}")
            red_turn = not red_turn
        except ValueError as e:
            print(f"错误: {e}")


def ai_vs_ai_mode():
    """AI 自对弈模式"""
    # 选择搜索深度
    try:
        red_depth_input = input("红方搜索深度 (1~8, 默认3): ").strip()
        black_depth_input = input("黑方搜索深度 (1~8, 默认3): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    red_depth = 3
    if red_depth_input.isdigit() and 1 <= int(red_depth_input) <= 8:
        red_depth = int(red_depth_input)
    black_depth = 3
    if black_depth_input.isdigit() and 1 <= int(black_depth_input) <= 8:
        black_depth = int(black_depth_input)

    # 选择最大步数
    try:
        max_input = input("最大步数 (默认200): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    max_moves = 200
    if max_input.isdigit() and int(max_input) > 0:
        max_moves = int(max_input)

    # 选择播放速度
    try:
        speed = input("播放方式 (Enter=逐步, a=自动): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    auto = speed == "a"

    red_ai = ChessAI(depth=red_depth)
    black_ai = ChessAI(depth=black_depth)
    print(f"\n  红方深度={red_depth} vs 黑方深度={black_depth}, 最大 {max_moves} 步\n")

    board = Board()
    board.display()
    red_turn = True

    for step in range(1, max_moves + 1):
        if check_game_over(board, red_turn):
            break

        side = "红方" if red_turn else "黑方"
        ai = red_ai if red_turn else black_ai

        move, info = ai.best_move(board, red_turn)
        if move is None:
            winner = "黑方" if red_turn else "红方"
            print(f"\n  === {winner}胜! ({side}无棋可走) ===")
            break

        print(f"\n  第 {step} 步 [{side}] {move}  "
              f"(深度={info['depth']}, 节点={info['nodes']}, "
              f"耗时={info['time']:.2f}s, 评分={info['score']})")

        try:
            captured = board.move(move)
            board.display()
            if captured != ".":
                print(f"  吃掉: {captured}")
        except ValueError as e:
            print(f"  走法错误: {e}")
            break

        if not auto:
            try:
                cmd = input("  (Enter=继续, q=退出) ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出自对弈")
                return
            if cmd.lower() in ("q", "quit", "exit"):
                return

        red_turn = not red_turn
    else:
        print(f"\n  === 达到最大步数 {max_moves}，和棋 ===")


def main():
    while True:
        print("\n中国象棋")
        print("  1. 对弈模式")
        print("  2. 棋谱模式")
        print("  3. 人机对弈")
        print("  4. AI 自对弈")
        print("  q. 退出")

        try:
            choice = input("\n选择: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if choice in ("q", "quit", "exit"):
            break
        elif choice == "1":
            play_mode()
        elif choice == "2":
            replay_mode()
        elif choice == "3":
            ai_mode()
        elif choice == "4":
            ai_vs_ai_mode()
        else:
            print("无效选择")


if __name__ == "__main__":
    main()
