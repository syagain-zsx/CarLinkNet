"""XGBoost 分类器（论文 3.3.1，行为时间结构特征分支基础模型）。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import xgboost as xgb

from .base import BaseClassifier, to_numpy


class XGBModel(BaseClassifier):
    def __init__(self, n_classes: int, n_features: int | None = None, **params):
        self.n_classes = n_classes
        self.n_features = n_features
        self.params = dict(
            objective="multi:softprob",
            eval_metric="mlogloss",
            max_depth=8,
            learning_rate=0.1,
            n_estimators=150,
            subsample=0.8,
            colsample_bytree=0.8,
            tree_method="hist",
            verbosity=0,
        )
        self.params.update(params)
        self.model: xgb.XGBClassifier | None = None

    def fit(self, X, y):
        X = to_numpy(X)
        y = np.asarray(y, dtype=int)
        self.n_features = X.shape[1]
        params = dict(self.params)
        params["num_class"] = self.n_classes
        self.model = xgb.XGBClassifier(**params)
        self.model.fit(X, y)
        return self

    def predict_proba(self, X) -> np.ndarray:
        X = to_numpy(X)
        p = self.model.predict_proba(X)
        full = np.zeros((len(X), self.n_classes), dtype=np.float32)
        n = min(p.shape[1], self.n_classes)
        full[:, :n] = p[:, :n]
        return full

    def num_parameters(self) -> int:
        return 0  # 树模型无参数量概念，体积以磁盘大小计

    def save(self, path: str | Path):
        self.model.save_model(str(path))

    def load(self, path: str | Path):
        self.model = xgb.XGBClassifier()
        self.model.load_model(str(path))
        return self
