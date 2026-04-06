## 配置说明

### 环境参数配置
环境参数统一在 `config/env_params.py` 中配置，包括：
- **技术指标列表** (`TECHNICAL_INDICATORS_LIST`): 定义使用的技术指标
- **环境参数** (`ENV_PARAMS`): 包含初始资金、交易成本、打印频率等

使用方式：
```python
from config import get_env_params

# 使用默认参数
env_params = get_env_params()
env = StockLearningEnv(df=data, **env_params)

# 覆盖特定参数
env_params = get_env_params(print_verbosity=100, random_start=False)
env = StockLearningEnv(df=data, **env_params)
```

### 模型参数配置
模型参数在 `config/model_params.py` 中配置，支持 A2C, PPO, DDPG, TD3, SAC 等模型。

## env install
### local_service_proxy
- 用于端口转发（公司通过云中介，访问家里的机器）
### git
- https://cnb.cool/davidhacking/stock_models
    Git Username:cnb
    Token:87xsYBby012fdnWIhPrUS5jYy8B
### python 
- 3.10 # linux conda python310
- source venv/bin/activate # 初始通过[requirements.txt](requirements.txt)安装 python lib
- windows 无法安装
### futu
- 下载实时行情
- 下载 [Futu_OpenD_8.6.4608_Ubuntu16.04](https://openapi.futunn.com/futu-api-doc/en/quick/opend-base.html)
- 启动 cd Futu_OpenD_8.6.4608_Ubuntu16.04 && ./FutuOpenD
- 登入账号 12316428
- 登入方式 账号密码
### tushare
- 下载天极更新行情
- 登入账号 13127563603
- token cd63754e5ee823494e89a68fedd374ed94a497e17142757096075add
### ths券商ui交易客户端
- docker windows git@github.com:dockur/windows.git
- compose.yml
```yaml
services:
  windows:
    image: dockurr/windows
    container_name: windows
    environment:
      VERSION: "11"
      DISK_SIZE: "256G"
      RAM_SIZE: "16G"
      CPU_CORES: "8"
      USERNAME: "windows"
      PASSWORD: "windows"
      LANGUAGE: "Chinese"
    volumes:
      - "/home/david/MF:/data"
    devices:
      - /dev/kvm
      - /dev/net/tun
    cap_add:
      - NET_ADMIN
    ports:
      - 8006:8006
      - 5555:5555
      - 3389:3389/tcp
      - 3389:3389/udp
    stop_grace_period: 2m
```
- start windows
```bash
docker compose stop windows
docker compose up -d --force-recreate
```
- 8.155.1.245:50051 pwd: win
- zx account 30300015679
- 运行 [ths_trader.py](brokerage/ths_trader.py)
```bash
conda activate easytrader
cd \\host.lan\Data\github\stock_models\brokerage
python ths_trader.py
```

## env
### reset
- 返回init_state（个人账户信息 现金+股票），类型np.array
- init_state[0] 现金
- init_state[1:n+1] 股票持仓
- init_state[n+1:] 股票当前收盘价
- n来自于init函数的df也就是Data.get_train_data or get_test_data返回的
### step
- 输入 actions: np.ndarray
```python
self.action_space = spaces.Box(low=-1, high=1, shape=(D,)) # D 股票只数
```
  - 返回的是每个股票的action，范围是 [-1, 1]
  - actions = actions * hmax 才是对于一只股票的买卖数据，hmax对于a股一般是5k
  - 此时actions变成了交易金额，需要再通过get_transactions转换为交易手数
- 输出 
  - `observation`: List - 新的环境状态
```python
D = len(self.assets) # 股票数量
b = 1 # 余额
h = D # 每只股票的持仓信息
p = D * len(self.daily_information_cols) # 股票的价格信息 包括各种技术指标
self.state_space = (
        b + h + p
)
self.observation_space = spaces.Box(
    low=-np.inf, high=np.inf, shape=(self.state_space,)
)
```
  - `reward`: float - 当前步的奖励值
    - 奖励计算逻辑: 最大化收益率，并且回撤率也最小，稳健的交易方式
```python
# 累计收益率 = (当前总资产 / 初始资金) - 1
# -回撤率 = (当前资产 / 历史最高资产) - 1（如果当前资产低于历史最高）
# 最终奖励 = 累计收益率 + alpha × -回撤率
```
  - `done`: bool - 是否结束回合
    - 交易到最后一天结束
    - 当前的action无法进行交易了
  - `info`: dict - 附加信息
    - 目前返回为空

## run方法
- cd tests
1. train 
```python
python -m unittest test_all_models.TestAllModels.test_all_models_with_multiprocessing
```
2. 加载账户信息 
```python
python -m unittest test_ths_account.TestThsUserStockAccountCurHolds
```
3. trade 
```python
python -m unittest test_ths_trader.TestThsTraderBySac.test_trader_by_sac
```
