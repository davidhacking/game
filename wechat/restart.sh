#!/usr/bin/env bash
#
# restart.sh — 重启微信 <-> Claude Code 桥接服务
#
# 流程：
#   1. 发 SIGTERM 给旧进程，让它优雅退出（保存同步游标到磁盘）
#   2. 等旧进程退出
#   3. 启动新进程（自动从磁盘恢复同步游标，不丢消息）
#
# 用法：
#   ./restart.sh          # 重启（后台运行）
#   ./restart.sh --fg     # 重启（前台运行，看日志）
#   ./restart.sh --stop   # 仅停止，不启动
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"
PID_FILE="$DATA_DIR/bridge.pid"
LOG_DIR="$DATA_DIR/logs"
LOG_FILE="$LOG_DIR/bridge.log"

mkdir -p "$DATA_DIR" "$LOG_DIR"

# ── 停止旧进程 ──────────────────────────────────────────────
stop_old() {
  if [ ! -f "$PID_FILE" ]; then
    echo "📭 没有发现运行中的进程 (无 PID 文件)"
    return 0
  fi

  local pid
  pid=$(cat "$PID_FILE" 2>/dev/null || true)

  if [ -z "$pid" ]; then
    echo "📭 PID 文件为空，跳过停止"
    rm -f "$PID_FILE"
    return 0
  fi

  # 检查进程是否存活
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "📭 进程 $pid 已不存在，清理 PID 文件"
    rm -f "$PID_FILE"
    return 0
  fi

  echo "🛑 正在停止旧进程 (PID: $pid)..."
  # SIGTERM: 让进程优雅退出，保存同步游标
  kill -TERM "$pid" 2>/dev/null || true

  # 等待进程退出，最多 15 秒
  local waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [ $waited -ge 15 ]; then
      echo "⚠️  进程 $pid 未在 15s 内退出，强制 kill"
      kill -9 "$pid" 2>/dev/null || true
      sleep 1
      break
    fi
    sleep 1
    waited=$((waited + 1))
  done

  rm -f "$PID_FILE"
  echo "✅ 旧进程已停止"
}

# ── 启动新进程 ──────────────────────────────────────────────
start_new() {
  local mode="${1:-bg}"

  echo "🚀 启动桥接服务..."

  if [ "$mode" = "fg" ]; then
    echo "   (前台模式，Ctrl+C 停止)"
    cd "$SCRIPT_DIR"
    exec npx tsx src/index.ts
  else
    cd "$SCRIPT_DIR"
    nohup npx tsx src/index.ts >> "$LOG_FILE" 2>&1 &
    local new_pid=$!
    echo "   PID: $new_pid"
    echo "   日志: $LOG_FILE"
    echo ""

    # 等 2 秒确认进程没有立即崩溃
    sleep 2
    if kill -0 "$new_pid" 2>/dev/null; then
      echo "✅ 桥接服务已在后台启动"
      echo ""
      echo "查看日志:  tail -f $LOG_FILE"
      echo "停止服务:  $SCRIPT_DIR/restart.sh --stop"
      echo "重新启动:  $SCRIPT_DIR/restart.sh"
    else
      echo "❌ 进程启动后立即退出，请检查日志:"
      tail -20 "$LOG_FILE"
      exit 1
    fi
  fi
}

# ── 主逻辑 ──────────────────────────────────────────────────
main() {
  local arg="${1:-}"

  case "$arg" in
    --stop)
      stop_old
      echo "👋 服务已停止"
      ;;
    --fg)
      stop_old
      start_new fg
      ;;
    *)
      stop_old
      start_new bg
      ;;
  esac
}

main "$@"
