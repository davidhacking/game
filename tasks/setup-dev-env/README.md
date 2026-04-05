# 项目开发环境安装

## 环境要求
- Ubuntu 22.04+ (x86_64)
- Node.js 22+ (已预装则跳过)
- Python 3.13+ (通过 uv 管理)

## 快速安装
```bash
bash setup.sh
```

## 手动安装步骤

### 1. 安装 uv (Python 包管理器)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 2. 安装 Python 3.13 并同步依赖
```bash
uv python install 3.13
cd /path/to/game
uv sync
```
项目根目录的 `.python-version` 指定 3.13，`uv sync` 会自动创建虚拟环境。

### 3. 安装 Node.js 依赖 (微信桥接服务)
```bash
cd wechat/
npm install
```

## 验证
```bash
# Python
uv run python --version          # 应输出 3.13.x
cd chinese_chess && uv run python test_moves.py  # 37 个测试全部通过

# Node.js (微信桥接)
cd wechat && npm run build       # TypeScript 编译无报错
```
