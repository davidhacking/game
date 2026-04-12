"""
V4 训练: 多ETF联合训练 LGB+XGB+CatBoost 三模型融合

核心逻辑:
1. 下载 90 只 A 股 ETF 日K (2015~今天)
2. 统一 build_features, 标签 = 多时间窗口融合收益率 (5d/10d/20d/30d加权)
3. LGB+XGB+CatBoost 三模型融合, purged time-series split
4. 保存模型 + 预测分布统计 (供 predict.py 做仓位映射)

回测请用 backtest.py --split_date
"""
import argparse
from datetime import datetime
import sys
sys.path.insert(0, '/home/david/MF/trade_a50_v2')
from scripts.core import *
from scripts.config import HORIZON_WEIGHTS, ENSEMBLE_MODELS


def build_training_data(use_cache=True):
    """构建多ETF联合训练数据"""
    cache_path = os.path.join(DATA_DIR, 'multi_etf_features.pkl')

    if use_cache and os.path.exists(cache_path):
        print('  Loading cached multi-ETF data...')
        all_data = pd.read_pickle(cache_path)
        print('  Cached: %d rows, %d ETFs' % (len(all_data), all_data['etf_code'].nunique()))
    else:
        print('  Downloading multi-ETF data...')
        raw = load_multi_etf(start='2015-01-01', min_rows=500)
        if len(raw) == 0:
            raise ValueError('No ETF data downloaded!')
        print('  Building features for each ETF...')
        all_dfs = []
        for code in raw['etf_code'].unique():
            etf_df = raw[raw['etf_code'] == code].copy()
            etf_df = build_features(etf_df)
            etf_df['etf_code'] = code
            all_dfs.append(etf_df)
        all_data = pd.concat(all_dfs, ignore_index=True)
        all_data.to_pickle(cache_path)
        print('  Saved cache: %s (%d rows)' % (cache_path, len(all_data)))

    # 标签: 多时间窗口融合 (5d/10d/20d/30d 加权平均)
    all_data['date'] = pd.to_datetime(all_data['date'])
    labeled = []
    for code in all_data['etf_code'].unique():
        etf_df = all_data[all_data['etf_code'] == code].sort_values('date').copy()
        c = etf_df['close']
        for days, weight in HORIZON_WEIGHTS.items():
            etf_df['ret_%dd_fwd' % days] = c.shift(-days) / c - 1
        # 加权融合: fused = Σ(weight_i × ret_i)
        etf_df['fused_target'] = sum(
            w * etf_df['ret_%dd_fwd' % d] for d, w in HORIZON_WEIGHTS.items()
        )
        labeled.append(etf_df)
    all_data = pd.concat(labeled, ignore_index=True)

    feat_cols = get_feature_cols(all_data)
    all_data = all_data.dropna(subset=feat_cols + ['fused_target'])
    print('  Horizon weights: %s' % HORIZON_WEIGHTS)
    print('  Final dataset: %d rows, %d features, %d ETFs' % (
        len(all_data), len(feat_cols), all_data['etf_code'].nunique()))
    return all_data, feat_cols


def train_model(all_data, feat_cols, split_date):
    """训练 LGB + XGBoost + CatBoost 三模型融合 (purged time-series split)"""
    import xgboost as xgb
    from scipy.stats import spearmanr

    split_dt = pd.Timestamp(split_date)
    purge_gap = pd.DateOffset(days=35)  # >= max horizon (30d) + buffer

    val_start = split_dt - pd.DateOffset(months=8)  # 8 months to compensate 35d purge gap
    train_mask = all_data['date'] < (val_start - purge_gap)
    val_mask = (all_data['date'] >= val_start) & (all_data['date'] < (split_dt - purge_gap))

    train_df = all_data[train_mask]
    val_df = all_data[val_mask]
    print('  Train: %d rows | Valid: %d rows' % (len(train_df), len(val_df)))

    X_train = train_df[feat_cols].values
    y_train = train_df['fused_target'].values
    X_val = val_df[feat_cols].values
    y_val = val_df['fused_target'].values

    N_ROUNDS = 3000
    models = {}
    preds_val = {}

    active_models = [m for m in ENSEMBLE_MODELS if m is not None]
    print('  Ensemble: %s' % active_models)

    for model_name in active_models:
        if model_name == 'lgb':
            print('  Training LightGBM (max %d rounds, early_stop=500)...' % N_ROUNDS)
            lgb_model = lgb.train(
                {
                    'objective': 'regression', 'metric': 'mae',
                    'learning_rate': 0.01, 'num_leaves': 63, 'max_depth': 7,
                    'subsample': 0.8, 'colsample_bytree': 0.6,
                    'lambda_l1': 5, 'lambda_l2': 20, 'min_child_samples': 50,
                    'verbose': -1,
                },
                lgb.Dataset(X_train, label=y_train),
                num_boost_round=N_ROUNDS,
                valid_sets=[lgb.Dataset(X_val, label=y_val)],
                callbacks=[lgb.early_stopping(500), lgb.log_evaluation(500)],
            )
            models['lgb'] = lgb_model
            preds_val['lgb'] = lgb_model.predict(X_val)
            print('    LGB best_iter=%d MAE=%.4f' % (lgb_model.best_iteration, np.mean(np.abs(preds_val['lgb'] - y_val))))

        elif model_name == 'xgb':
            print('  Training XGBoost (max %d rounds, early_stop=500)...' % N_ROUNDS)
            xgb_model = xgb.XGBRegressor(
                objective='reg:squarederror', eval_metric='mae',
                learning_rate=0.01, max_depth=7, n_estimators=N_ROUNDS,
                subsample=0.8, colsample_bytree=0.6,
                reg_alpha=5, reg_lambda=20, min_child_weight=50,
                early_stopping_rounds=500, verbosity=0,
            )
            xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
            models['xgb'] = xgb_model
            preds_val['xgb'] = xgb_model.predict(X_val)
            print('    XGB best_iter=%d MAE=%.4f' % (xgb_model.best_iteration, np.mean(np.abs(preds_val['xgb'] - y_val))))

        elif model_name == 'cb':
            from catboost import CatBoostRegressor
            print('  Training CatBoost (max %d rounds, early_stop=500)...' % N_ROUNDS)
            cb_model = CatBoostRegressor(
                iterations=N_ROUNDS, learning_rate=0.01, depth=7,
                l2_leaf_reg=20, subsample=0.8, rsm=0.6,
                early_stopping_rounds=500, verbose=0, loss_function='MAE',
            )
            cb_model.fit(X_train, y_train, eval_set=(X_val, y_val))
            models['cb'] = cb_model
            preds_val['cb'] = cb_model.predict(X_val).flatten()
            print('    CB  best_iter=%d MAE=%.4f' % (cb_model.best_iteration_, np.mean(np.abs(preds_val['cb'] - y_val))))

        elif model_name == 'ft_transformer':
            from scripts.ft_transformer import FTTransformerRegressor
            print('  Training FT-Transformer...')
            ft = FTTransformerRegressor(n_features=len(feat_cols))
            ft.fit(X_train, y_train, X_val, y_val)
            models['ft_transformer'] = ft
            preds_val['ft_transformer'] = ft.predict(X_val)
            print('    FT  MAE=%.4f' % np.mean(np.abs(preds_val['ft_transformer'] - y_val)))

    # ── 融合: 所有模型等权平均 ──
    n_models = len(preds_val)
    val_pred = sum(preds_val.values()) / n_models
    fused_mae = np.mean(np.abs(val_pred - y_val))

    # 截面 IC
    cross_ic, _ = spearmanr(val_pred, y_val)
    # 时序 IC (每只 ETF 内逐日)
    val_df_copy = val_df.copy()
    val_df_copy['pred'] = val_pred
    ts_ics = []
    for etf in val_df_copy['etf_code'].unique():
        sub = val_df_copy[val_df_copy['etf_code'] == etf].sort_values('date')
        if len(sub) >= 20:
            ic_val, _ = spearmanr(sub['pred'].values, sub['fused_target'].values)
            if not np.isnan(ic_val):
                ts_ics.append(ic_val)
    ts_ic = float(np.mean(ts_ics)) if ts_ics else 0.0
    ic = ts_ic

    print('  ── Ensemble ──')
    mae_parts = ' '.join('%s=%.4f' % (k, np.mean(np.abs(v - y_val))) for k, v in preds_val.items())
    print('  MAE: %s → Fused=%.4f' % (mae_parts, fused_mae))
    print('  Time-series IC: %.4f (avg over %d ETFs) | Cross-sectional IC: %.4f' % (ts_ic, len(ts_ics), cross_ic))

    # 训练集预测分布 (用融合预测)
    from scripts.core import ensemble_predict
    train_pred = ensemble_predict(models, X_train)

    pred_stats = {
        'mean': float(np.mean(train_pred)),
        'std': float(np.std(train_pred)),
        'p10': float(np.percentile(train_pred, 10)),
        'p25': float(np.percentile(train_pred, 25)),
        'p50': float(np.percentile(train_pred, 50)),
        'p75': float(np.percentile(train_pred, 75)),
        'p90': float(np.percentile(train_pred, 90)),
    }
    print('  Pred distribution: mean=%.4f std=%.4f [p10=%.4f, p50=%.4f, p90=%.4f]' % (
        pred_stats['mean'], pred_stats['std'], pred_stats['p10'], pred_stats['p50'], pred_stats['p90']))

    ensemble = models
    return ensemble, ic, fused_mae, pred_stats


def train(split_date_str, no_cache=False):
    sd = '%s-%s-%s' % (split_date_str[:4], split_date_str[4:6], split_date_str[6:])

    print('=' * 60)
    print('  V4 Train | split: %s' % sd)
    print('  90 ETFs joint training, LGB+XGB+CatBoost ensemble')
    print('=' * 60)

    # 1. 构建多ETF训练数据
    all_data, feat_cols = build_training_data(use_cache=not no_cache)

    # 2. 训练三模型融合
    model, ic, mae, pred_stats = train_model(all_data, feat_cols, sd)

    # 3. 保存模型 + 元数据
    meta = {
        'split_date': sd,
        'model_type': 'ensemble_v5_configurable',
        'ic': round(ic, 4),
        'mae': round(mae, 6),
        'pred_stats': pred_stats,
        'horizon_weights': HORIZON_WEIGHTS,
        'n_features': len(feat_cols),
        'feature_cols': feat_cols,
        'n_etfs_trained': all_data['etf_code'].nunique(),
        'n_train_rows': len(all_data),
        'trained_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    save_model(model, meta)

    print('\n' + '=' * 60)
    print('  Done! IC: %.4f | MAE: %.4f | Trained on %d ETFs (%d rows)' % (
        ic, mae, all_data['etf_code'].nunique(), len(all_data)))
    print('  Model saved to %s' % MODEL_DIR)
    print('  Run backtest: ./backtest.sh %s' % split_date_str)
    print('=' * 60)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--split_date', default='20250101')
    p.add_argument('--no_cache', action='store_true', help='Force re-download all ETF data')
    args = p.parse_args()
    train(args.split_date, args.no_cache)
