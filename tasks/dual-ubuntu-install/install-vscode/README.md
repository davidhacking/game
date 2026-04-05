# 安装 VS Code - Ubuntu 22.04

## 环境
- Ubuntu 22.04 LTS (jammy), x86_64

## 方案
通过微软官方 APT 仓库安装，后续可直接 `apt upgrade` 更新。

## 安装步骤
1. 安装依赖并添加微软 GPG 密钥
2. 添加微软 APT 仓库
3. `apt install code` 安装 VS Code

## 使用
```bash
bash install_vscode.sh
```

## 启动
```bash
code                  # 启动 VS Code
code /path/to/project # 打开指定项目
```
