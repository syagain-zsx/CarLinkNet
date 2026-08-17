"""简化版 FT-Transformer（论文 3.3.1，多尺度频域特征分支基础模型）。

将每个特征映射为一个 feature token，通过多头自注意力建模特征间全局依赖，
以 CLS token 汇聚全局信息完成分类。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from .base import BaseClassifier, to_numpy, train_classifier, torch_proba, torch_logits, set_seed


class FTTransformer(nn.Module):
    def __init__(self, n_features: int, n_classes: int, d_token: int = 32,
                 n_layers: int = 2, n_heads: int = 4):
        super().__init__()
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_token))
        self.embed = nn.Linear(1, d_token)
        layer = nn.TransformerEncoderLayer(
            d_model=d_token, nhead=n_heads, dim_feedforward=64,
            batch_first=True, dropout=0.1,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.head = nn.Linear(d_token, n_classes)

    def forward(self, x):
        # x: (batch, n_features) -> tokens (batch, n_features, d_token)
        tokens = self.embed(x.unsqueeze(-1))
        cls = self.cls_token.expand(x.shape[0], -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)
        encoded = self.encoder(tokens)
        return self.head(encoded[:, 0, :])


class FTTModel(BaseClassifier):
    def __init__(self, n_classes: int, n_features: int | None = None, d_token: int = 32,
                 n_layers: int = 2, n_heads: int = 4, epochs: int = 30, lr: float = 1e-3, seed: int = 0):
        self.n_classes = n_classes
        self.n_features = n_features
        self.d_token = d_token
        self.n_layers = n_layers
        self.n_heads = n_heads
        self.epochs = epochs
        self.lr = lr
        self.seed = seed
        self.model: FTTransformer | None = None

    def _build(self, n_features: int):
        set_seed(self.seed)
        self.n_features = n_features
        self.model = FTTransformer(n_features, self.n_classes, self.d_token, self.n_layers, self.n_heads)

    def fit(self, X, y):
        X = to_numpy(X)
        if self.model is None or self.n_features != X.shape[1]:
            self._build(X.shape[1])
        train_classifier(self.model, X, y, epochs=self.epochs, lr=self.lr)
        return self

    def predict_proba(self, X) -> np.ndarray:
        return torch_proba(self.model, X)

    def predict_logits(self, X) -> np.ndarray:
        return torch_logits(self.model, X)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.model.parameters())

    def save(self, path: str | Path):
        torch.save(self.model.state_dict(), path)

    def load(self, path: str | Path):
        state = torch.load(path, map_location="cpu", weights_only=True)
        if self.model is None:
            self._build(self.n_features)
        self.model.load_state_dict(state)
        self.model.eval()
        return self
