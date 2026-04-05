# Project Memory

## Project Overview
- **Project**: 中国象棋（Chinese Chess）游戏 + 微信桥接服务
- **Python**: 3.13+，包管理器 uv
- **Node.js**: TypeScript，用于微信桥接

## Project Structure
- `chinese_chess/` - 象棋核心代码
  - `board.py` - 棋盘表示与规则
  - `alpha_beta.py` - Alpha-Beta 搜索 AI
  - `chess_engine.py` - 引擎封装
  - `endgames.py` - 残局库
  - `games.py` / `gen_games.py` / `gen_endgames.py` - 棋谱与残局生成
  - `main.py` - 游戏主程序（人机对弈/AI自弈等模式）
  - `test_*.py` - 测试用例
- `wechat/` - 微信 <-> Claude Code 桥接服务（TypeScript）
- `tasks/` - 任务文档目录（每个任务一个文件夹，含 README.md）
- `start_game.py` - 快捷启动人机对弈脚本
- `XIANGQI_ANALYSIS.md` - 棋局分析文档

## User Preferences
- Preferred language for communication: 中文 (Chinese)
- **每次修改完代码后，必须运行所有测试用例，确保全部通过后才算完成**
- **遇到一个 badcase 时，必须修复这一类问题，而不是只修单个点**
- **新任务流程**：在 `tasks/` 目录下创建以任务命名的文件夹，先出 `README.md`（任务说明/方案文档），再添加脚本等其他文件

## Session Log
<!-- Claude will append notes here about what was done in each session -->
