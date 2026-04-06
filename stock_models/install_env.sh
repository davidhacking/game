#!/bin/bash

# 定义虚拟环境的目录名称
ENV_NAME="venv" # 您可以根据需要更改此名称

echo "正在创建 Python 虚拟环境: $ENV_NAME"

# 创建虚拟环境
python -m venv $ENV_NAME

# 激活虚拟环境
source $ENV_NAME/bin/activate

echo "正在升级 pip..."
pip install --upgrade pip

echo "正在使用 requirements.txt 安装依赖..."

# 使用 pip 安装 requirements.txt 中列出的所有包
pip install -r requirements.txt

echo "环境 $ENV_NAME 安装完成。请运行 'source $ENV_NAME/bin/activate' 来使用。"
