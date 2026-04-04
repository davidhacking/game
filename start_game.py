#!/usr/bin/env python3
"""启动人机对弈脚本 - 红方玩家 vs 黑方AI"""

import sys
import subprocess
import time

# 启动人机对弈，选择完整开局，执红方，默认搜索深度
commands = [
    "3",           # 选择人机对弈模式
    "1",           # 选择完整开局
    "1",           # 执红方
    "",            # 默认搜索深度5
]

print("正在启动中国象棋人机对弈...")
print("你执红方，AI执黑方")
print("游戏即将开始...\n")

time.sleep(1)

# 启动游戏进程
proc = subprocess.Popen(
    ["uv", "run", "python", "chinese_chess/main.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# 发送初始命令
for cmd in commands:
    proc.stdin.write(cmd + "\n")
    proc.stdin.flush()
    time.sleep(0.5)

# 让用户接管交互
print("游戏已启动！现在你可以输入走法了。")
print("走法格式：ICCS坐标如 b0c2 (马八进七)")
print("提示：按 h 查看可走棋步，按 q 退出\n")

# 输出游戏内容
while True:
    line = proc.stdout.readline()
    if not line:
        break
    print(line, end='')

proc.wait()