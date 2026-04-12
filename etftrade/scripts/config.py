"""
交易配置

BUY_LIST:  允许买入的标的, predict 只对这些发 BUY 信号
其他持仓:  模型预测收益率, 预测跌就建议卖出
"""

# 允许买入的标的 (FutuOpenD 格式)
BUY_LIST = [
    'SH.588000',  # 科创50 ETF
]

# 其他持仓卖出阈值: 预测值 < pred_stats 的哪个分位数就卖
# p25 = 后25%, 比较保守; p50 = 后50%, 比较激进
SELL_THRESHOLD_PERCENTILE = 'p25'

# 多时间窗口融合权重 (5d/10d/20d/30d)
# 短期(5d)捕捉动量, 中期(10d/20d)主力, 长期(30d)趋势
HORIZON_WEIGHTS = {
    5:  0.15,
    10: 0.30,
    20: 0.30,
    30: 0.25,
}

# 渐进调仓: 指数衰减追踪
# 每天实际调仓 = (目标仓位 - 当前仓位) × POSITION_SPEED
# 0.3 表示每天只走差距的30%, 约5~7天到达目标
# 好处: 大调仓时分批建仓/减仓, 小微调时一步到位
POSITION_SPEED = 0.3

# 最小调仓阈值: 渐进后的实际调仓幅度 < 此值就不交易
MIN_REBALANCE = 0.05

# 融合模型列表: 支持 'lgb', 'xgb', 'cb', 'ft_transformer', None(跳过)
# 平权融合, prediction = mean(各模型预测)
ENSEMBLE_MODELS = ['lgb', 'xgb', 'ft_transformer']
