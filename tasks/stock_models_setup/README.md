# stock_models 环境搭建与脚本封装

## 任务目标
1. 将 `~/Downloads/stock_models.tar.gz` 解压到 `game/stock_models/`
2. 用 **uv**（非 conda）创建独立 Python 虚拟环境，仅对 `stock_models/` 生效
3. 封装两个脚本：
   - `train.py`：训练所有强化学习模型
   - `predict.py`：加载模型预测，输出当前的买卖列表

---

## 项目理解

### 项目结构
```
stock_models/
├── config/          # 参数配置（env_params, model_params, stock_codes）
├── data/            # 数据层（tushare拉取A50股票数据）
├── environments/    # gym强化学习环境
├── rl_agent/        # StockAgent（封装stable_baselines3模型）
├── utils/           # transaction转换、同花顺交易接口
├── account/         # 同花顺账户
├── brokerage/       # 券商接口
├── tests/           # 测试用例
└── requirements.txt
```

### 工作流程
1. **数据**：通过 tushare 拉取上证50成分股（SSE_50_EXT，52只股票）的日K行情 + 技术指标
2. **训练**：`A50Data.update()` → `StockLearningEnv` + `StockAgent.train()` → 保存模型 `.zip`
3. **预测/交易**：加载模型 → 构建 observation（余额 + 持仓 + 技术指标） → `agent.predict()` → 转换为实际买卖股数

### 模型支持
- A2C, PPO, DDPG, TD3, SAC（stable_baselines3）

### Python 版本
- 原项目使用 Python 3.10（原 venv 来自 macOS 3.10.4）
- Linux 系统自带 Python 3.10.12，兼容

---

## 环境安装方案

### 使用 uv（替代 conda）
```bash
cd /home/david/MF/github/game/stock_models
uv venv .venv --python 3.10   # 重建 .venv（原来的 .venv 是 macOS 下的）
uv pip install -r requirements.txt
```

- `.venv` 在 `stock_models/` 目录内，只对该项目生效
- 不影响 `game/` 根目录的 uv 环境

---

## 封装脚本说明

### train.py
- 位置：`stock_models/train.py`
- 功能：更新数据 → 并发训练所有模型（A2C/PPO/DDPG/TD3/SAC）→ 保存到 `tests/models/`
- 参数：`--timesteps`（训练步数，默认200000）、`--models`（指定模型，默认全部）

### predict.py
- 位置：`stock_models/predict.py`
- 功能：更新数据 → 加载指定模型 → 预测 action → 转换为买卖列表并输出
- 输出格式：
  ```
  买入: [(股票代码, 数量, 价格), ...]
  卖出: [(股票代码, 数量, 价格), ...]
  持有: [股票代码, ...]
  ```
- 参数：`--model`（指定模型名称，默认SAC）

---

## 执行记录

### 2026-04-06
- [x] 解压 tar.gz 到 game/stock_models/
- [x] 安装 uv（通过 `python3 -m pip install uv`，安装到 ~/.local/bin/uv）
- [x] 重建 .venv（原 .venv 是 macOS 3.10.4 环境，用 uv 重建为 Linux Python 3.10.12）
  - 命令：`/home/david/.local/bin/uv venv .venv --python 3.10`
- [x] 安装依赖（核心包全部安装成功，跳过 Windows-only 包 pywinauto/comtypes/easytrader/atari-py）
  - torch 2.11.0+cu130, stable-baselines3 1.2.0, gym 0.26.2, tushare, stockstats, futu-api 等全部 OK
  - 注意：sub agent 安装时遭遇网络中断，最终通过主 agent 直接安装完成
- [x] 创建 train.py 脚本
- [x] 创建 predict.py 脚本

### 问题记录
（执行过程中如遇到问题记录于此）
