#!/usr/bin/env python3
"""
象棋引擎 JSON 接口 — 供 Node.js 子进程调用
每次调用传入一个 JSON 命令，返回一个 JSON 结果，然后退出。

用法:
  echo '{"action":"new"}' | python3 chess_engine.py
  echo '{"action":"move","fen":"...","move":"b0c2","red_turn":true}' | python3 chess_engine.py
  echo '{"action":"ai_move","fen":"...","red_turn":false,"depth":3}' | python3 chess_engine.py
"""
import sys
import json
import os

# 确保能导入 chinese_chess 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board import Board
from alpha_beta import ChessAI


def board_to_fen(board: Board) -> str:
    """将棋盘转为 FEN 字符串（仅棋子布局部分）"""
    rows = []
    for r in range(10):
        row_str = ""
        empty = 0
        for c in range(9):
            piece = board.grid[r][c]
            if piece == ".":
                empty += 1
            else:
                if empty > 0:
                    row_str += str(empty)
                    empty = 0
                row_str += piece
        if empty > 0:
            row_str += str(empty)
        rows.append(row_str)
    return "/".join(rows)


def fen_to_board(fen: str) -> Board:
    """从 FEN 字符串恢复棋盘"""
    board = Board()
    rows = fen.split("/")
    for r in range(10):
        c = 0
        for ch in rows[r]:
            if ch.isdigit():
                for _ in range(int(ch)):
                    board.grid[r][c] = "."
                    c += 1
            else:
                board.grid[r][c] = ch
                c += 1
    return board


def board_to_text(board: Board) -> str:
    """渲染棋盘为文本"""
    return str(board)


def get_legal_moves(board: Board, red: bool) -> list[str]:
    """获取所有合法走法（ICCS 格式）"""
    moves_dict = board.generate_moves(red=red)
    result = []
    for (r1, c1), dests in moves_dict.items():
        for (r2, c2) in dests:
            iccs = chr(ord('a') + c1) + str(9 - r1) + chr(ord('a') + c2) + str(9 - r2)
            result.append(iccs)
    return result


def is_in_check(board: Board, red: bool) -> bool:
    """检查是否被将军"""
    return board._is_in_check(red)


def is_checkmate(board: Board, red: bool) -> bool:
    """检查是否被将杀（无合法走法）"""
    moves = board.generate_moves(red=red)
    return len(moves) == 0


def handle_command(cmd: dict) -> dict:
    action = cmd.get("action", "")

    if action == "new":
        board = Board()
        return {
            "ok": True,
            "fen": board_to_fen(board),
            "board": board_to_text(board),
            "red_moves": get_legal_moves(board, red=True),
        }

    elif action == "move":
        fen = cmd.get("fen", "")
        move_str = cmd.get("move", "")
        red_turn = cmd.get("red_turn", True)

        if not fen or not move_str:
            return {"ok": False, "error": "缺少 fen 或 move 参数"}

        board = fen_to_board(fen)

        # 验证走法合法性
        legal = get_legal_moves(board, red=red_turn)
        if move_str not in legal:
            return {
                "ok": False,
                "error": f"非法走法: {move_str}",
                "legal_moves": legal,
            }

        board.move(move_str)
        new_fen = board_to_fen(board)

        # 检查对方状态
        opponent_red = not red_turn
        in_check = is_in_check(board, opponent_red)
        checkmate = is_checkmate(board, opponent_red)

        return {
            "ok": True,
            "fen": new_fen,
            "board": board_to_text(board),
            "move": move_str,
            "in_check": in_check,
            "checkmate": checkmate,
        }

    elif action == "ai_move":
        fen = cmd.get("fen", "")
        red_turn = cmd.get("red_turn", False)
        depth = cmd.get("depth", 3)

        if not fen:
            return {"ok": False, "error": "缺少 fen 参数"}

        board = fen_to_board(fen)

        # 先检查是否已经无路可走
        if is_checkmate(board, red_turn):
            return {
                "ok": True,
                "fen": fen,
                "board": board_to_text(board),
                "move": None,
                "checkmate": True,
                "winner": "黑方" if red_turn else "红方",
            }

        ai = ChessAI(depth=depth)
        move, info = ai.best_move(board, red_turn=red_turn)

        if not move:
            return {
                "ok": True,
                "fen": fen,
                "board": board_to_text(board),
                "move": None,
                "checkmate": True,
                "winner": "黑方" if red_turn else "红方",
            }

        board.move(move)
        new_fen = board_to_fen(board)

        # 检查走完后对方的状态
        opponent_red = not red_turn
        in_check = is_in_check(board, opponent_red)
        checkmate = is_checkmate(board, opponent_red)

        return {
            "ok": True,
            "fen": new_fen,
            "board": board_to_text(board),
            "move": move,
            "in_check": in_check,
            "checkmate": checkmate,
            "winner": ("红方" if red_turn else "黑方") if checkmate else None,
        }

    elif action == "board":
        fen = cmd.get("fen", "")
        if not fen:
            return {"ok": False, "error": "缺少 fen 参数"}
        board = fen_to_board(fen)
        red_turn = cmd.get("red_turn", True)
        return {
            "ok": True,
            "fen": fen,
            "board": board_to_text(board),
            "legal_moves": get_legal_moves(board, red=red_turn),
        }

    else:
        return {"ok": False, "error": f"未知命令: {action}"}


def main():
    try:
        raw = sys.stdin.read()
        cmd = json.loads(raw)
        result = handle_command(cmd)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
