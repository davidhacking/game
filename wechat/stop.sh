#!/usr/bin/env bash
# stop.sh — 停止微信 <-> Claude Code 桥接服务
set -euo pipefail
exec "$(dirname "$0")/restart.sh" --stop
