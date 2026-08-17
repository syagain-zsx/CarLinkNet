"""一维卷积神经网络（论文 3.3.1，统计特征分支基础模型）。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from .base import BaseClassifier, to_numpy, train_classifier, torch_proba, torch_logits, set_seed


class CNN1D(nn.Module):
    def __init__(self, n_features: int, n_classes: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(1, hidden, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(hidden, hidden * 2, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(hidden * 2, n_classes),
        )

    def forward(self, x):
        # x: (batch, n_features) -> (batch, 1, n_features)
        return self.net(x.unsqueeze(1))


class CNNModel(BaseClassifier):
    def __init__(self, n_classes: int, n_features: int | None = None, hidden: int = 64,
                 epochs: int = 30, lr: float = 1e-3, seed: int = 0):
        self.n_classes = n_classes
        self.n_features = n_features
        self.hidden = hidden
        self.epochs = epochs
        self.lr = lr
        self.seed = seed
        self.model: CNN1D | None = None

    def _build(self, n_features: int):
        set_seed(self.seed)
        self.n_features = n_features
        self.model = CNN1D(n_features, self.n_classes, self.hidden)

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
            # 需要 n_features 才能重建结构；此处要求先设置 n_features
            self._build(self.n_features)
        self.model.load_state_dict(state)
        self.model.eval()
        return self
