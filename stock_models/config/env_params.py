"""
环境参数配置
包含技术指标列表和环境初始化参数
"""

# 技术指标列表
TECHNICAL_INDICATORS_LIST = [
    "boll_ub",  # BOLL 指标上轨线 股价应始终处于股价信道内运行，若股价突破上轨线，则表明股价处于超买状态，提醒观察者可以适当减仓
    "boll_lb",  # BOLL 指标下轨线
    "rsi_20", 
    "close_20_sma", 
    "close_60_sma", 
    "close_120_sma",
    "macd", 
    "volume_20_sma", 
    "volume_60_sma", 
    "volume_120_sma"
]

# 信息列
INFORMATION_COLS = TECHNICAL_INDICATORS_LIST + [
    "close", 
    "day", 
    "amount", 
    "change", 
    "daily_variance",
    "pe_ratio"
]

# 环境默认参数
ENV_PARAMS = {
    "initial_amount": 1e6,
    "hmax": 5000,  # speed money not trade stock num
    "currency": '￥',
    "buy_cost_pct": 3e-3,
    "sell_cost_pct": 3e-3,
    "cache_indicator_data": True,
    "daily_information_cols": INFORMATION_COLS, 
    "print_verbosity": 500,
    "patient": True,
    "alpha": 0.5,
    "normalize_buy_sell": True,
    "state_init_func": "AllCashStateIntiator",
}


def get_env_params(**kwargs) -> dict:
    """
    获取环境参数，支持自定义覆盖
    
    Args:
        **kwargs: 需要覆盖的参数
        
    Returns:
        dict: 环境参数字典
    """
    params = ENV_PARAMS.copy()
    params.update(kwargs)
    return params
