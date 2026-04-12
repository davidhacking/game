"""
核心模块: FutuOpenD数据获取 + 特征加工 + 模型存取 + Kelly计算
"""
import os, json, pickle, time, warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import lightgbm as lgb
from futu import OpenQuoteContext, KLType, RET_OK

MODEL_DIR  = '/home/david/MF/trade_a50_v2/models'
DATA_DIR   = '/home/david/MF/trade_a50_v2/data'
RESULT_DIR = '/home/david/MF/trade_a50_v2/results'
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

INITIAL_CASH = 1_000_000
LOT_SIZE     = 100
# ETF: 佣金万2.5双向, 无印花税, 无过户费
BUY_COST  = 0.00025
SELL_COST = 0.00025

DEFAULT_ETF = "SH.588000"

FUTU_HOST = os.environ.get('FUTU_HOST', '127.0.0.1')
FUTU_PORT = int(os.environ.get('FUTU_PORT', '11111'))


# ==================================================================
# FutuOpenD 数据获取
# ==================================================================
def _futu_kline(code, start, end):
    """从 FutuOpenD 下载日K线 (自动分页)"""
    ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
    all_data = []
    page_key = None
    while True:
        kwargs = dict(code=code, start=start, end=end, ktype=KLType.K_DAY, max_count=1000)
        if page_key:
            kwargs['page_req_key'] = page_key
        ret, data, page_key = ctx.request_history_kline(**kwargs)
        if ret == RET_OK:
            all_data.append(data)
        else:
            print('  FutuOpenD error (%s): %s' % (code, data))
            break
        if page_key is None:
            break
        time.sleep(0.5)
    ctx.close()
    if not all_data:
        return pd.DataFrame()
    df = pd.concat(all_data, ignore_index=True)
    df['date'] = pd.to_datetime(df['time_key']).dt.strftime('%Y-%m-%d')
    df = df.rename(columns={'turnover': 'amount'})
    for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
        if col in df.columns:
            df[col] = df[col].astype(float)
    df = df.sort_values('date').reset_index(drop=True)
    return df


def load_data(code, start='2020-01-01', end='2027-01-01'):
    """
    从 FutuOpenD 获取数据, 落一份CSV缓存

    Args:
        code: FutuOpenD格式, 如 'SH.588000', 'SH.000016'
        start/end: 日期范围

    Returns:
        DataFrame with OHLCV + date
    """
    # 缓存文件名
    safe_code = code.replace('.', '_')
    cache_path = os.path.join(DATA_DIR, '%s.csv' % safe_code)

    # 尝试增量更新: 如果缓存存在, 只下载最新部分
    cached = None
    if os.path.exists(cache_path):
        cached = pd.read_csv(cache_path)
        cached['date'] = pd.to_datetime(cached['date']).dt.strftime('%Y-%m-%d')
        last_date = cached['date'].max()
        if last_date >= end[:10]:
            print('  Cache hit: %s (%d rows, up to %s)' % (cache_path, len(cached), last_date))
            return cached
        # 增量: 从 last_date 后一天开始下载
        fetch_start = (pd.Timestamp(last_date) + pd.DateOffset(days=1)).strftime('%Y-%m-%d')
        print('  Incremental update: %s -> %s' % (last_date, end[:10]))
    else:
        fetch_start = start

    # 从 FutuOpenD 下载
    print('  Fetching %s from FutuOpenD (%s ~ %s)...' % (code, fetch_start, end[:10]))
    new_data = _futu_kline(code, fetch_start, end)

    if len(new_data) == 0 and cached is not None:
        return cached

    # 只保留需要的列
    keep = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
    new_data = new_data[[c for c in keep if c in new_data.columns]]

    # 合并缓存
    if cached is not None and len(new_data) > 0:
        df = pd.concat([cached, new_data], ignore_index=True)
        df = df.drop_duplicates(subset='date', keep='last').sort_values('date').reset_index(drop=True)
    elif len(new_data) > 0:
        df = new_data
    else:
        df = cached if cached is not None else pd.DataFrame()

    # 保存缓存
    if len(df) > 0:
        df.to_csv(cache_path, index=False)
        print('  Saved cache: %s (%d rows)' % (cache_path, len(df)))

    return df


# ==================================================================
# 技术指标加工
# ==================================================================
def build_features(df):
    """在OHLCV基础上加工技术指标"""
    f = df.copy()
    f['date'] = pd.to_datetime(f['date'])
    c = f['close'].astype(float)
    h = f['high'].astype(float)
    l = f['low'].astype(float)
    v = f['volume'].astype(float)

    # RSI
    delta = c.diff()
    gain = delta.where(delta > 0, 0).rolling(20).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(20).mean()
    f['rsi_20'] = 100 - (100 / (1 + gain / loss))

    # MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    f['macd'] = ema12 - ema26
    f['macd_signal'] = f['macd'].ewm(span=9, adjust=False).mean()
    f['macd_hist'] = f['macd'] - f['macd_signal']

    # Bollinger Bands
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    f['boll_ub'] = ma20 + 2 * std20
    f['boll_lb'] = ma20 - 2 * std20

    # 均线
    f['ma5'] = c.rolling(5).mean()
    f['ma10'] = c.rolling(10).mean()
    f['close_20_sma'] = ma20
    f['close_60_sma'] = c.rolling(60).mean()
    f['close_120_sma'] = c.rolling(120).mean()

    # 均量
    f['volume_20_sma'] = v.rolling(20).mean()
    f['volume_60_sma'] = v.rolling(60).mean()
    f['volume_120_sma'] = v.rolling(120).mean()

    # 日变化
    f['change'] = c.pct_change()
    f['daily_variance'] = (h - l) / c
    f['day'] = f['date'].dt.dayofweek

    # ---- 衍生特征 ----
    for d in [1, 2, 3, 5, 10, 20, 60]:
        f['ret_%d' % d] = c.pct_change(d)
    for col in ['ma5', 'ma10', 'close_20_sma', 'close_60_sma', 'close_120_sma']:
        if col in f.columns:
            f['bias_' + col] = (c - f[col]) / f[col]
    f['boll_pos'] = (c - f['boll_lb']) / (f['boll_ub'] - f['boll_lb'] + 1e-8)
    f['boll_width'] = (f['boll_ub'] - f['boll_lb']) / c
    for d_col in ['volume_20_sma', 'volume_60_sma']:
        f['vol_ratio_' + d_col] = v / (f[d_col] + 1)
    for d in [5, 10, 20, 60]:
        f['std_%d' % d] = f['change'].rolling(d).std()
    for d in [5, 10, 20, 60]:
        f['highlow_%d' % d] = (c - l.rolling(d).min()) / (h.rolling(d).max() - l.rolling(d).min() + 1e-8)
    f['pv_corr'] = f['change'].rolling(20).corr(v.pct_change())
    f['ma_score'] = (
        (f['ma5'] > f['ma10']).astype(float) +
        (f['ma10'] > f['close_20_sma']).astype(float) +
        (f['close_20_sma'] > f['close_60_sma']).astype(float) +
        (f['close_60_sma'] > f['close_120_sma']).astype(float)
    )
    f['macd_diff'] = f['macd'] - f['macd'].shift(1)
    f['macd_acc'] = f['macd_diff'] - f['macd_diff'].shift(1)
    f['amplitude'] = (h - l) / c
    f['amplitude_ma5'] = f['amplitude'].rolling(5).mean()
    for d in [10, 20, 60]:
        f['slope_%d' % d] = c.rolling(d).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == d else 0, raw=False)
    if 'amount' in f.columns:
        f['amount_ratio'] = f['amount'] / f['amount'].rolling(20).mean()

    return f


def get_feature_cols(df):
    """获取可用特征列"""
    exclude = {'date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'day',
               'label', 'future_ret', 'future_up', 'future_5d', 'fused_target',
               'ret_5d_fwd', 'ret_10d_fwd', 'ret_20d_fwd', 'ret_30d_fwd'}
    return [c for c in df.columns if c not in exclude and df[c].dtype in ['float64', 'float32', 'int64']]


# ==================================================================
# 模型存取
# ==================================================================
def ensemble_predict(model, X):
    """根据 model dict 动态调用各模型, 等权平均"""
    preds = []
    for name, m in model.items():
        p = m.predict(X)
        preds.append(np.array(p).flatten())
    return np.mean(preds, axis=0)


def save_model(model, meta):
    # FT-Transformer 单独保存 (PyTorch 不能 pickle)
    ft = model.pop('ft_transformer', None)
    if ft:
        ft.save(os.path.join(MODEL_DIR, 'ft_transformer.pt'))
    # 其余模型 (lgb/xgb/cb) pickle
    with open(os.path.join(MODEL_DIR, 'model.pkl'), 'wb') as f:
        pickle.dump(model, f)
    # 恢复引用
    if ft:
        model['ft_transformer'] = ft
    with open(os.path.join(MODEL_DIR, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=2, default=str)

def load_model():
    with open(os.path.join(MODEL_DIR, 'model.pkl'), 'rb') as f:
        model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, 'meta.json'), 'r') as f:
        meta = json.load(f)
    # 尝试加载 FT-Transformer
    ft_path = os.path.join(MODEL_DIR, 'ft_transformer.pt')
    if os.path.exists(ft_path):
        from scripts.ft_transformer import FTTransformerRegressor
        model['ft_transformer'] = FTTransformerRegressor.load(ft_path)
    return model, meta


# ==================================================================
# Kelly 仓位
# ==================================================================
def kelly_position(prob, odds, kelly_frac=0.5, max_pos=0.95):
    f = prob - (1 - prob) / odds
    if f <= 0:
        return 0.0
    return min(kelly_frac * f, max_pos)


# ==================================================================
# 批量 ETF 数据 (多ETF联合训练用)
# ==================================================================
def get_etf_list():
    """
    A 股 ETF 训练宇宙: 旧版71只宽基为基础 + 新增科技行业ETF

    设计思路:
    - 同一指数的多只ETF (如沪深300×5) 并非"重复数据"
      它们走势高度相似, 等于给模型提供了更多同类样本, 对学习科创50的模式有帮助
    - 在旧版基础上补充科技/半导体/AI等行业ETF, 增强与科创50的关联数据
    """
    from futu import OpenQuoteContext, RET_OK
    ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
    ret, data = ctx.get_plate_stock('SH.BK0800')
    ctx.close()
    if ret != RET_OK:
        print('  Error getting ETF list:', data)
        return []
    etfs = data[data['stock_name'].str.contains('ETF', case=False)]
    exclude_kw = ['货币','快线','理财','活期','保证金','债','利率','黄金',
                  '大宗商品','纳指','标普','德国','恒生','日利','添益','联接','快钱']
    for kw in exclude_kw:
        etfs = etfs[~etfs['stock_name'].str.contains(kw)]
    base = list(zip(etfs['code'].tolist(), etfs['stock_name'].tolist()))

    # 新增科技/行业ETF (旧版BK0800中没有的)
    extra = [
        ('SH.588050', '科创板50ETF华夏'),
        ('SH.588080', '科创板50ETF易方达'),
        ('SH.512760', '芯片ETF国泰'),
        ('SH.512720', '计算机ETF'),
        ('SZ.159998', '计算机ETF天弘'),
        ('SH.515230', '软件ETF'),
        ('SH.515880', '通信ETF'),
        ('SH.515260', '电子ETF'),
        ('SH.515070', '人工智能ETF华夏'),
        ('SH.562500', '机器人ETF'),
        ('SH.512480', '半导体ETF'),
        ('SZ.159806', '新能源车ETF'),
        ('SH.515790', '光伏ETF'),
        ('SH.512660', '军工ETF'),
        ('SH.512400', '有色金属ETF'),
        ('SH.515220', '煤炭ETF'),
        ('SH.512200', '房地产ETF'),
        ('SH.512800', '银行ETF'),
        ('SH.512100', '中证1000ETF'),
    ]
    # 去重
    base_codes = set(c for c, _ in base)
    for code, name in extra:
        if code not in base_codes:
            base.append((code, name))
    return base


def load_multi_etf(etf_list=None, start='2015-01-01', end='2027-01-01', min_rows=500):
    """
    批量下载多只ETF，合并成一个大DataFrame用于联合训练

    Returns:
        DataFrame with columns: date, open, high, low, close, volume, amount, etf_code
    """
    if etf_list is None:
        etf_list = get_etf_list()
    all_dfs = []
    for i, (code, name) in enumerate(etf_list):
        print('  [%d/%d] %s %s ...' % (i+1, len(etf_list), code, name), end='')
        try:
            df = load_data(code, start=start, end=end)
            if len(df) < min_rows:
                print(' skip (%d rows < %d)' % (len(df), min_rows))
                continue
            df['etf_code'] = code
            all_dfs.append(df)
            print(' ok (%d rows)' % len(df))
        except Exception as e:
            print(' error: %s' % e)
        time.sleep(0.3)  # FutuOpenD rate limit
    if not all_dfs:
        return pd.DataFrame()
    merged = pd.concat(all_dfs, ignore_index=True)
    print('  Total: %d ETFs, %d rows' % (len(all_dfs), len(merged)))
    return merged


def kelly_position_continuous(expected_return, variance, kelly_frac=0.5, max_pos=0.95):
    """连续Kelly公式: f = mu / sigma^2, 取半Kelly"""
    if variance <= 0 or expected_return <= 0:
        return 0.0
    f = expected_return / variance
    return min(kelly_frac * f, max_pos)


def pred_to_position(pred_ret, pred_stats):
    """
    将模型预测值映射为目标仓位 (分位数映射)

    仓位区间:
      pred <= p10          → 0%  (强烈看跌, 清仓)
      pred p10~p25         → 15%~30% (轻仓防守)
      pred p25~p50         → 30%~60% (适中持仓)
      pred p50~p75         → 60%~85% (重仓)
      pred > p75           → 85%~95% (准满仓)

    模型是唯一决策者, 没有硬编码的MA/RSI/MACD规则
    """
    p10 = pred_stats['p10']
    p25 = pred_stats['p25']
    p50 = pred_stats['p50']
    p75 = pred_stats['p75']
    p90 = pred_stats['p90']

    if pred_ret <= p10:
        return 0.0
    elif pred_ret <= p25:
        ratio = (pred_ret - p10) / (p25 - p10) if p25 > p10 else 0.5
        return 0.15 + 0.15 * ratio
    elif pred_ret <= p50:
        ratio = (pred_ret - p25) / (p50 - p25) if p50 > p25 else 0.5
        return 0.30 + 0.30 * ratio
    elif pred_ret <= p75:
        ratio = (pred_ret - p50) / (p75 - p50) if p75 > p50 else 0.5
        return 0.60 + 0.25 * ratio
    elif pred_ret <= p90:
        ratio = (pred_ret - p75) / (p90 - p75) if p90 > p75 else 0.5
        return 0.85 + 0.10 * ratio
    else:
        return 0.95
