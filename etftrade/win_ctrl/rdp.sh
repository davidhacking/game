#!/usr/bin/env bash
# 快速连接 Windows RDP
# 用法：bash rdp.sh

xfreerdp \
    /v:localhost:3389 \
    /u:windows \
    /p:windows \
    /sound:sys:pulse \
    /dynamic-resolution \
    /cert:ignore \
    /scale:140 &

echo "RDP 已启动（PID=$!）"
