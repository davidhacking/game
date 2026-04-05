#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================="
echo "  项目开发环境安装脚本"
echo "========================================="

# ---------- 1. 安装 uv ----------
echo ""
echo "[1/4] 安装 uv (Python 包管理器)..."
if command -v uv &>/dev/null; then
    echo "uv 已安装: $(uv --version)"
else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "uv 安装完成: $(uv --version)"
fi

# ---------- 2. 安装 Python 3.13 ----------
echo ""
echo "[2/4] 安装 Python 3.13..."
if uv python list --only-installed 2>/dev/null | grep -q "3.13"; then
    echo "Python 3.13 已安装"
else
    uv python install 3.13
    echo "Python 3.13 安装完成"
fi

# ---------- 3. 同步 Python 依赖 ----------
echo ""
echo "[3/4] 同步 Python 项目依赖..."
cd "$PROJECT_ROOT"
uv sync
echo "Python 依赖同步完成"

# ---------- 4. 安装 Node.js 依赖 ----------
echo ""
echo "[4/4] 安装 Node.js 依赖 (微信桥接服务)..."
if ! command -v node &>/dev/null; then
    echo "⚠️  Node.js 未安装，请先安装 Node.js 22+"
    echo "   推荐: curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs"
else
    cd "$PROJECT_ROOT/wechat"
    npm install
    echo "Node.js 依赖安装完成"
fi

# ---------- 验证 ----------
echo ""
echo "========================================="
echo "  验证安装结果"
echo "========================================="

cd "$PROJECT_ROOT"

echo -n "  Python: "
uv run python --version

echo -n "  uv: "
uv --version

echo -n "  Node.js: "
node --version 2>/dev/null || echo "未安装"

echo -n "  npm: "
npm --version 2>/dev/null || echo "未安装"

echo ""
echo "  运行象棋走法测试..."
cd "$PROJECT_ROOT/chinese_chess"
uv run python test_moves.py 2>&1 | tail -1

echo ""
echo "  编译微信桥接服务..."
cd "$PROJECT_ROOT/wechat"
if npm run build 2>&1 | grep -q "error"; then
    echo "  ❌ TypeScript 编译失败"
else
    echo "  ✅ TypeScript 编译成功"
fi

echo ""
echo "========================================="
echo "  ✅ 开发环境安装完成！"
echo "========================================="
