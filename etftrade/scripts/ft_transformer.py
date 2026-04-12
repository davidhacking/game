"""
FT-Transformer 回归器封装

对外接口和 sklearn/GBDT 一致: fit(), predict(), save(), load()
内部自动处理: 特征归一化 + GPU检测 + 早停 + 模型保存

FT-Transformer 论文: "Revisiting Deep Learning Models for Tabular Data" (NeurIPS 2021)
特点: 所有数值特征统一做 token 化, 参与 self-attention, 适合纯数值特征的回归任务
"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler


class FTTransformerRegressor:
    """FT-Transformer 回归器, 对外接口和 LGB/XGB 一致"""

    def __init__(self, n_features, dim=32, depth=4, heads=8, dropout=0.1, lr=1e-3):
        self.n_features = n_features
        self.dim = dim
        self.depth = depth
        self.heads = heads
        self.dropout = dropout
        self.lr = lr
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.scaler = StandardScaler()
        self.model = None
        self._build_model()

    def _build_model(self):
        """构建 FT-Transformer"""
        from tab_transformer_pytorch import FTTransformer
        self.model = FTTransformer(
            categories=(),                # 无类别特征
            num_continuous=self.n_features,  # 50个数值特征
            dim=self.dim,                  # embedding 维度
            depth=self.depth,              # Transformer 层数
            heads=self.heads,              # 注意力头数
            dim_out=1,                     # 回归: 输出1个值
            attn_dropout=self.dropout,
            ff_dropout=self.dropout,
        ).to(self.device)

    def fit(self, X_train, y_train, X_val=None, y_val=None,
            epochs=200, batch_size=512, patience=30):
        """
        训练 FT-Transformer

        Args:
            X_train/y_train: numpy array, 训练数据
            X_val/y_val: numpy array, 验证数据 (用于早停)
            epochs: 最大轮数
            batch_size: 批大小
            patience: 早停耐心 (验证集MAE连续patience轮没进步就停)
        """
        # 归一化 (FT-Transformer 需要, GBDT 不需要)
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val) if X_val is not None else None

        # 转 tensor
        train_X = torch.FloatTensor(X_train_scaled).to(self.device)
        train_y = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)
        train_ds = TensorDataset(train_X, train_y)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

        if X_val_scaled is not None:
            val_X = torch.FloatTensor(X_val_scaled).to(self.device)
            val_y = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)

        # 优化器 + 损失
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.L1Loss()  # MAE, 和 GBDT 的 metric 一致

        # 训练循环
        best_val_mae = float('inf')
        best_state = None
        patience_counter = 0

        for epoch in range(epochs):
            # ── 训练 ──
            self.model.train()
            train_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                # FTTransformer 需要: (categories, numericals)
                pred = self.model(torch.tensor([], dtype=torch.long).to(self.device).expand(batch_X.size(0), 0), batch_X)
                loss = criterion(pred, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item() * batch_X.size(0)
            train_loss /= len(train_ds)
            scheduler.step()

            # ── 验证 ──
            if X_val_scaled is not None:
                self.model.eval()
                with torch.no_grad():
                    val_pred = self.model(torch.tensor([], dtype=torch.long).to(self.device).expand(val_X.size(0), 0), val_X)
                    val_mae = criterion(val_pred, val_y).item()

                if val_mae < best_val_mae:
                    best_val_mae = val_mae
                    best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                    patience_counter = 0
                else:
                    patience_counter += 1

                if (epoch + 1) % 20 == 0 or epoch == 0:
                    print('    FT epoch %3d: train_mae=%.4f val_mae=%.4f best=%.4f%s' % (
                        epoch + 1, train_loss, val_mae, best_val_mae,
                        ' *' if patience_counter == 0 else ''))

                if patience_counter >= patience:
                    print('    FT early stopping at epoch %d, best_val_mae=%.4f' % (epoch + 1, best_val_mae))
                    break

        # 恢复最佳权重
        if best_state is not None:
            self.model.load_state_dict(best_state)
        self.model.eval()
        return self

    def predict(self, X, batch_size=4096):
        """
        预测, 返回 numpy array (分批推理, 防止 GPU OOM)

        和 lgb_model.predict(X) 接口一致:
          输入: numpy array, shape (n_samples, n_features)
          输出: numpy array, shape (n_samples,)
        """
        self.model.eval()
        X_scaled = self.scaler.transform(X)
        all_preds = []
        for i in range(0, len(X_scaled), batch_size):
            batch = torch.FloatTensor(X_scaled[i:i+batch_size]).to(self.device)
            with torch.no_grad():
                empty_cat = torch.tensor([], dtype=torch.long).to(self.device).expand(batch.size(0), 0)
                pred = self.model(empty_cat, batch)
            all_preds.append(pred.cpu().numpy().flatten())
        return np.concatenate(all_preds)

    def save(self, path):
        """保存: 模型权重 + scaler + 超参数"""
        torch.save({
            'model_state': self.model.state_dict(),
            'scaler_mean': self.scaler.mean_,
            'scaler_scale': self.scaler.scale_,
            'n_features': self.n_features,
            'dim': self.dim,
            'depth': self.depth,
            'heads': self.heads,
            'dropout': self.dropout,
            'lr': self.lr,
        }, path)

    @classmethod
    def load(cls, path):
        """加载模型"""
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        obj = cls(
            n_features=checkpoint['n_features'],
            dim=checkpoint['dim'],
            depth=checkpoint['depth'],
            heads=checkpoint['heads'],
            dropout=checkpoint['dropout'],
            lr=checkpoint['lr'],
        )
        obj.model.load_state_dict(checkpoint['model_state'])
        obj.model.eval()
        obj.scaler.mean_ = checkpoint['scaler_mean']
        obj.scaler.scale_ = checkpoint['scaler_scale']
        obj.scaler.n_features_in_ = checkpoint['n_features']
        return obj
